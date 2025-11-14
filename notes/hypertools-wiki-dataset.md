# Hypertools Wikipedia Dataset

## Dataset Access

The hypertools library includes a Wikipedia dataset with 3,136 articles.

### Correct Way to Load

```python
import hypertools as hyp

# Load the dataset
wiki_data = hyp.load('wiki')

# Get the actual article text
article_text = wiki_data.get_data()

# Structure:
# - article_text is a list with 1 element
# - article_text[0] is a numpy array with shape (3136,)
# - Each element is a string containing the full article text
```

### Example Usage

```python
import hypertools as hyp
import numpy as np

# Load
article_text = hyp.load('wiki').get_data()

# article_text is a list containing one numpy array
articles_array = article_text[0]  # shape: (3136,)

# Each element is the full article text as a single string
print(f"Total articles: {len(articles_array)}")
print(f"First article length: {len(articles_array[0])}")
print(f"First 100 chars: {articles_array[0][:100]}...")

# To convert to a list of articles:
articles_list = [str(article) for article in articles_array]
```

## Limitations

**No article titles**: The dataset contains only the full text of each article, with no separate title field or metadata. Article titles appear at the beginning of the text but are not delimited.

## Decision: Not Using Hypertools Dataset

**Reason**: We have 250,000 Wikipedia articles from the Dropbox pickle file that include proper structure (title, text, url, id). The hypertools dataset:
- Has no titles or metadata
- Only 3,136 articles (1.2% of our dataset)
- Adds minimal value compared to the 250k articles we already have

**Conclusion**: Removed from [build_wikipedia_knowledge_map_v2.py](../build_wikipedia_knowledge_map_v2.py) to simplify the build process and focus on the higher-quality 250k article dataset.
