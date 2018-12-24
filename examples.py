from nlg import Narrative as N
import pandas as pd

print(N('Hello, world!'))

print(N('{name}, in week {week}, you spent most of your time in {project}',
        name='Anand', week=49, project='Dell'))

print(N(['{project} was what you spent most of your time in week {week}, {name}.',
         '{name}, in week {week}, you spent most of your time in {project}',
         'Week {week}: your top project was {project}'],
        name='Anand', week=49, project='Dell'))


df = pd.read_csv('data/assembly.csv')
df['vote_share'] = df.pop(
    'Vote share').apply(lambda x: x.replace('%', '')).astype(float)
tmpl = """BJP won a voteshare of {x}% in {y}, followed by {a}% in {b} and
{c}% in {d}."""
n = N(tmpl, data=df,
      x='{data.vote_share[0]}', y='{data.AC[0]}',
      a='{data.vote_share[1]}', b='{data.AC[1]}',
      c='{data.vote_share[2]}', d='{data.AC[2]}')
print(n)
