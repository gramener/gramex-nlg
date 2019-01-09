from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import humanize as hmn
from nlg import NLGTemplate as N
from nlg import utils


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

###############################################################################
# Fancy templating with tornado ###############################################
###############################################################################

df = pd.DataFrame.from_dict({'project': ['Dell', 'Ambit', 'Star']})
df['this_week'] = np.random.rand(3,)
df['last_week'] = np.random.rand(3,)
df[['this_week', 'last_week']] /= df[['this_week', 'last_week']].sum(0)

bit = lambda x, y: abs((x - y) / x) > 0.1  # NOQA: E731
lot = lambda x, y: abs((x - y) / x) > 0.33  # NOQA: E731
compare = lambda x, y: utils.humanize_comparison(x, y, bit, lot)  # NOQA: E731


# In[6]:

t = '''
{{ name }},
    {{ humanize.naturaltime(last_ts).capitalize() }},
    you worked on {% if len(df) == 1 %}the{% end %} {{ utils.concatenate_items(df['project']) }}
    {{ utils.pluralize_by_seq('project', by=df['project']) }}.
    {{utils.pluralize('this project', by=df['project'])}} took
    {{ '{x:%}'.format(x=time_pc) }} of your time.

    {% for prj in range((len(df))) %}
        {{prj + 1}}. The time spent on {{ df['project'][prj] }} this week is
            {{ compare(df['last_week'][prj], df['this_week'][prj]) }}
    {% end %}
'''
last_ts = datetime.now() - timedelta(days=6)
print(N(t, tornado_tmpl=True, name='Anand', humanize=hmn, last_ts=last_ts,
        utils=utils, df=df,
        compare=compare, time_pc=df['this_week'].sum()).render())
