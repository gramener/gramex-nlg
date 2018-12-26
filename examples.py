from nlg import Narrative as N
import pandas as pd


###############################################################################
# Simple text formatting examples  #############################################
###############################################################################

print(N('Hello, world!'))
# Hello, world!

print(N('{name}, in week {week}, you spent most of your time in {project}',
        name='Anand', week=49, project='Dell'))
# Anand, in week 49, you spent most of your time in Dell

# Randomly picking a template.
print(N(['{project} was what you spent most of your time in week {week}, {name}.',
         '{name}, in week {week}, you spent most of your time in {project}',
         'Week {week}: your top project was {project}'],
        name='Anand', week=49, project='Dell'))


# Referring to dataframes from the template.
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

###############################################################################
# Using complex templates for more control  ####################################
###############################################################################
struct = {
    'intent': 'extreme',   # pick template automatically from intent
    'data': df,
    'metadata': {
        'subject': 'BJP',   # literal subject
        'verb': ['won', 'scored', 'achieved'],   # randomly sample a verb
        # randomly sample an adjective
        'adjective': ['highest', 'greatest', 'most', 'largest'],
        'object': {   # A PoS can have its own template
            'template': 'vote share of {value} in {location}',
            'location': {  # kwarg of the template
                '_type': 'cell',
                'colname': 'AC',   # the column from which `location` is to be picked
                # The operation `max` to be applied to the `vote_share` column
                '_filter': {'colname': 'vote_share', 'filter': 'max'}
            },
            'value': {  # another kwarg of the template
                '_type': 'cell',
                'colname': 'Vote share (%)',
                '_filter': 'max'
            }
        }
    }
}

print(N(struct=struct).render())


struct = {
    'intent': 'extreme',
    'data': df,
    'metadata': {
        'subject': 'BJP',
        'verb': ['won', 'scored', 'achieved'],
        'adjective': ['highest', 'greatest', 'most', 'largest'],
        'object': {
            'template': 'vote share of {value} in {location}',
            'location': {
                '_type': 'cell',
                'colname': 'AC',
                '_filter': 'max(vote_share)'   # simpler way of writing a filter
            },
            'value': {
                '_type': 'cell',
                'colname': 'Vote share (%)',
                '_filter': 'max'
            }
        }
    }
}
print(N(struct=struct).render())


df = pd.DataFrame.from_dict({
    'singer': ['Kishore', 'Kishore', 'Kishore'],
    'partner': ['Lata', 'Asha', 'Rafi'],
    'n_songs': [20, 5, 15]
})
struct = {
    'intent': 'extreme',
    'data': df,
    'metadata': {
        'subject': {
            '_type': 'cell',
            'colname': 'singer',
            '_filter': 'mode'
        },
        'verb': 'sang',
        'adjective': 'most',
        'object': {
            'template': 'duets with {partner}',
            'partner': {
                '_type': 'cell',
                'colname': 'partner',
                '_filter': 'max(n_songs)'
            }
        }
    }
}
print(N(struct=struct).render())


# making comparisons
df = pd.DataFrame.from_dict({
    'character': ['Eddard Stark', 'Jon Snow'],
    'n_episodes': [10, 56],
    'time_per_episode': [6.2, 5.5]
})
struct = {
    'intent': 'comparison',
    'data': df,
    'metadata': {
        'subject': {
            'template': '{character}\'s screen time per episode',
            'character': {
                '_type': 'cell',
                'colname': 'character',
                '_filter': 'max(time_per_episode)'
            }
        },
        'verb': 'is',
        'quant': {
            'template': '{q} minutes',
            'q': {
                '_type': 'operation',
                'expr': '{data.iloc[0].time_per_episode} - {data.iloc[1].time_per_episode}'
            }
        },
        'adjective': 'more',
        'object': {
            'template': 'that of {character}',
            'character': {
                '_type': 'cell',
                'colname': 'character',
                '_filter': 'min(time_per_episode)'
            }
        }
    }
}
print(N(struct=struct).render())
