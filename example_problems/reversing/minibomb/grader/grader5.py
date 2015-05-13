"""
Grader file for Minibomb problem
"""

def grade(autogen, key):
  indices = [(ord(x) & 0xf) for x in key]
  arr = "isrveawhobpnutfg"
  s = ''.join(arr[x] for x in indices)
  if s == 'giants':
    return (True, 'Good work!')
  else:
    return (False, 'Nope')
