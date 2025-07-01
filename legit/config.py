import re
from legit.lockfile import Lockfile

class ConfigError(Exception):
    pass

class ConflictError(ConfigError):
    pass

class ParseError(ConfigError):
    pass

class ConfigFile:
    SECTION_LINE = re.compile(r'^\s*\[([a-z0-9-]+)( "(.+)")?\]\s*($|#|;)', re.IGNORECASE)
    VARIABLE_LINE = re.compile(r'^\s*([a-z][a-z0-9-]*)\s*=\s*(.*?)\s*($|#|;)', re.IGNORECASE | re.MULTILINE)
    BLANK_LINE = re.compile(r'^\s*($|#|;)')
    INTEGER = re.compile(r'^-?[1-9][0-9]*$')

    VALID_SECTION = re.compile(r'^[a-z0-9-]+$', re.IGNORECASE)
    VALID_VARIABLE = re.compile(r'^[a-z][a-z0-9-]*$', re.IGNORECASE)

    class Line:
        def __init__(self, text, section, variable=None):
            self.text = text
            self.section = section
            self.variable = variable

        @property
        def normal_variable(self):
            return ConfigFile.Variable.normalize(self.variable.name if self.variable else None)

    class Section:
        def __init__(self, name):
            self.name = name

        @staticmethod
        def normalize(name):
            if not name:
                return []
            return [name[0].lower()] + [".".join(name[1:])] if len(name) > 1 else [name[0].lower()]


        def heading_line(self):
            line = f"[{self.name[0]}"
            if len(self.name) > 1:
                line += f' "{self.name[1]}"'
            line += "]\n"
            return line

    class Variable:
        def __init__(self, name, value):
            self.name = name
            self.value = value

        @staticmethod
        def normalize(name):
            return name.lower() if name else None

        @staticmethod
        def serialize(name, value):
            return f"\t{name} = {value}\n"

    @staticmethod
    def valid_key(key):
        return ConfigFile.VALID_SECTION.match(key[0]) and ConfigFile.VALID_VARIABLE.match(key[-1])

    def __init__(self, path):
        self.path = path
        self.lockfile = Lockfile(path)
        self.lines = None

    def open(self):
        if self.lines is None:
            self.read_config_file()

    def open_for_update(self):
        self.lockfile.hold_for_update()
        self.read_config_file()

    def save(self):
        for section, lines in self.lines.items():
            for line in lines:
                self.lockfile.write(line.text.encode('utf-8'))
        self.lockfile.commit()
        
    def list(self):
        """Returns a list of all 'key=value' pairs."""
        all_vars = []
        for section_key, lines in self.lines.items():
            section_name_parts = list(filter(None, section_key))
            
            for line in lines:
                if line.variable:
                    full_key = f"{'.'.join(section_name_parts)}.{line.variable.name}"
                    all_vars.append(f"{full_key}={line.variable.value}")
        return all_vars

    def get(self, key):
        return self.get_all(key)[-1] if self.get_all(key) else None

    def get_all(self, key):
        key, var = self.split_key(key)
        _, lines = self.find_lines(key, var)
        return [line.variable.value for line in lines]

    def add(self, key, value):
        key, var = self.split_key(key)
        section, _ = self.find_lines(key, var)
        self.add_variable(section, key, var, value)

    def set(self, key, value):
        if value is None:
            return

        key, var = self.split_key(key)
        section, lines = self.find_lines(key, var)

        if len(lines) == 0:
            self.add_variable(section, key, var, value)
        elif len(lines) == 1:
            self.update_variable(lines[0], var, value)
        else:
            raise ConflictError("cannot overwrite multiple values with a single value")

    def replace_all(self, key, value):
        key, var = self.split_key(key)
        section, lines = self.find_lines(key, var)
        self.remove_all(section, lines)
        self.add_variable(section, key, var, value)

    def unset(self, key):
        def check_conflict(lines):
            if len(lines) > 1:
                raise ConflictError(f"{key} has multiple values")
        self.unset_all(key, check_conflict)

    def unset_all(self, key, block=None):
        key, var = self.split_key(key)
        section, lines = self.find_lines(key, var)

        if not section:
            return
        
        if block:
            block(lines)

        self.remove_all(section, lines)
        section_lines = self.lines_for(section)
        if len(section_lines) == 1:
            self.remove_section(key)

    def remove_section(self, key):
        key = tuple(self.Section.normalize(key))
        return self.lines.pop(key, None) is not None

    def subsections(self, name):
        name, _ = self.Section.normalize([name])
        sections = []
        for main, sub in self.lines.keys():
            if main == name and sub != "":
                sections.append(sub)
        return sections

    def section_exists(self, key):
        key = tuple(self.Section.normalize(key))
        return key in self.lines

    def line_count(self):
        return sum(len(lines) for lines in self.lines.values())

    def lines_for(self, section):
        return self.lines[tuple(self.Section.normalize(section.name))]

    def split_key(self, key):
        key = [str(k) for k in key]
        var = key.pop()
        return key, var

    def find_lines(self, key, var):
        name = tuple(self.Section.normalize(key))
        if name not in self.lines:
            return None, []

        lines = self.lines[name]
        section = lines[0].section
        normal_var = self.Variable.normalize(var)

        return section, [l for l in lines if normal_var == l.normal_variable]

    def add_section(self, key):
        section = self.Section(key)
        line = self.Line(section.heading_line(), section)
        
        # Ensure the key is a tuple for dictionary access
        normalized_key = tuple(self.Section.normalize(section.name))
        if normalized_key not in self.lines:
            self.lines[normalized_key] = []

        self.lines[normalized_key].append(line)
        return section

    def add_variable(self, section, key, var, value):
        if section is None:
            section = self.add_section(key)

        text = self.Variable.serialize(var, value)
        variable = self.Variable(var, value)
        line = self.Line(text, section, variable)
        
        normalized_key = tuple(self.Section.normalize(section.name))
        self.lines[normalized_key].append(line)


    def update_variable(self, line, var, value):
        line.variable.value = value
        line.text = self.Variable.serialize(var, value)

    def remove_all(self, section, lines_to_remove):
        section_lines = self.lines_for(section)
        for line in lines_to_remove:
            if line in section_lines:
                section_lines.remove(line)

    def read_config_file(self):
        self.lines = {}
        section = self.Section([])

        try:
            with open(self.path, 'r') as f:
                content = f.read()
                
            current_pos = 0
            while current_pos < len(content):
                line_text, current_pos = self.read_line_from_content(content, current_pos)
                line_obj = self.parse_line(section, line_text)
                section = line_obj.section
                
                normalized_key = tuple(self.Section.normalize(section.name))
                if normalized_key not in self.lines:
                    self.lines[normalized_key] = []
                self.lines[normalized_key].append(line_obj)

        except FileNotFoundError:
            pass # It's okay if the config file doesn't exist yet

    def read_line_from_content(self, content, start_pos):
        end_pos = content.find('\n', start_pos)
        if end_pos == -1:
            end_pos = len(content)
        
        line = content[start_pos:end_pos+1]
        
        # Handle line continuations
        while line.endswith('\\\n'):
            start_pos = end_pos + 1
            end_pos = content.find('\n', start_pos)
            if end_pos == -1:
                end_pos = len(content)
            line += content[start_pos:end_pos+1]

        return line, end_pos + 1

    def parse_line(self, section, line):
        match = self.SECTION_LINE.match(line)
        if match:
            name_parts = [match.group(1)]
            if match.group(3):
                name_parts.append(match.group(3))
            section = self.Section(name_parts)
            return self.Line(line, section)

        match = self.VARIABLE_LINE.match(line)
        if match:
            variable = self.Variable(match.group(1), self.parse_value(match.group(2)))
            return self.Line(line, section, variable)

        if self.BLANK_LINE.match(line):
            return self.Line(line, section, None)

        raise ParseError(f"bad config line {self.line_count() + 1} in file {self.path}")

    def parse_value(self, value):
        value = value.strip()
        if value.lower() in ["yes", "on", "true"]:
            return True
        if value.lower() in ["no", "off", "false"]:
            return False
        if self.INTEGER.match(value):
            return int(value)
        # Handle string literals that might be quoted
        if value.startswith('"') and value.endswith('"'):
             # Unescape characters and remove quotes
            return value[1:-1].replace('\\"', '"').replace('\\\\', '\\').replace('\\\n', '')
        return value.replace('\\\n', '')

