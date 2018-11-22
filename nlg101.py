#!/usr/bin/env python
# coding: utf-8

# In[7]:


nugget = {
    'filter': {
        'column': 'Party',
        'value': 'Rajasthan',
        'type': 'groupy'
    },
    'result': {
        'metric': 'Count',
        'type': 'largest',
        'value': {
            'name': 'INC',
            'value': 0.58,
            'unit': None
        }
    }
}


# In[5]:


tokens = {'top_filter': 'the state of Rajasthan', 'by': 'the party', 'metric': 'highest % of wins', 'value': '58%'}


# In[38]:


import pandas as pd
import csv


# In[55]:


df = pd.read_csv('bollywood.celebrity.csv')


# In[56]:


df.head()


# In[67]:


df.groupby('name')['role'].count().sort_values(ascending=False).head()


# In[ ]:


# What did we do?
# We grouped by name, counted roles in each group and saw the highest
# Ideal text -> Lata Mangeshkar is the celebrity with the most roles.
# Reverse engineering the groupby statement:


# ## The name with the highest role count is Lata Mangeshkar.

# In[ ]:


nugget = {
    'filter': {
        'column': 'name',
        'select': 'role',
        'type': 'groupby'
    },
    'result': {
        'metric': 'count',
        'type': 'largest',
        'value': {
            'name': 'Lata Mangeshkar',
            'value': 824
        }
    }
}
