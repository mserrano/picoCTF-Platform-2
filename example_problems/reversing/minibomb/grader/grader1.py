"""
Grader file for Minibomb problem
"""

def grade(autogen, key):
  if 'Public speaking is very easy.' in key:
    return (True, 'Good work!')
  else:
    return (False, 'Nope')
