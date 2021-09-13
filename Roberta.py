import os
import random

# A random integer between 1 and 40
num = random.randint(1, 3)

def make_commit(days: int):
    if days < 1:
       return os.system('git push')
    else:
      mess = ['git commit -am "added new changes"','git commit -am "added Enhancemenets"','git commit -am "Bug fixes"','git commit -am "Documentataion"']
      with open('data.txt', 'a') as file:
         file.write(mess[num])

      os.system('git add data.txt')
      # os.sendline("testing")
      os.system(mess[num])
      os.system('git push')
      return days * make_commit(days-1)

make_commit(4)