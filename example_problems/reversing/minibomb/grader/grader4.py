"""
Grader file for Minibomb problem
"""

def grade(autogen, key):
  if '9' in key:
    return (True, 'Good work!')
  else:
    return (False, 'Nope')
