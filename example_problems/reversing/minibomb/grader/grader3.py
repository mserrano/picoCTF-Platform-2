"""
Grader file for Minibomb problem
"""

def grade(autogen, key):
  a, b, c = key.split(' ')
  a = int(a)
  c = int(c)
  b = ord(b)
  possibilities = [
    (0, 113, 777), (1, 98, 214), (2, 98, 755),
    (3, 107, 251), (4, 111, 160), (5, 116, 458),
    (6, 118, 780), (7, 98, 524)
  ]
  if ((a, b, c)) in possibilities:
    return (True, 'Good work!')
  else:
    return (False, 'Nope')
