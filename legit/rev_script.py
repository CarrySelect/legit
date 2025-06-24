from legit.revision import Revision

revstr = "@~3^"

print(Revision.parse(revstr))
