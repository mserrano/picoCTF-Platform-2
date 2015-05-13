"""
Grader file for Minibomb problem
"""

def grade(autogen, key):
  if '1 2 6 24 120 720' in key:
    return (True, 'Good work!')
  else:
    return (False, 'Nope')
