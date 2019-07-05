import numpy as np
import pandas as pd
import re
import feedparser
import html_text
from nltk import sent_tokenize
import itertools
import string


countries = {
    'cn': 'China',
    'fr': 'France',
#    'se': 'Sweden',
    'us': 'United States',
#    'jp': 'Japan',
    'mx': 'Mexico',
#    'sa': 'Saudi Arabia',
#    'ru': 'Russia'
}

genre_ids = ['1324']  # Society & Culture


def clean_text(text, normalize_cn_punct=False, normalize_url=False, remove_punctuations=False, remove_spaces=False, lower=False, line_break_replacement='[EOL]'):
    # Apply common replacements
    text = re.sub('&#(\d+);', lambda x: chr(int(x.group(1), 10)), text)  # https://stackoverflow.com/a/5040961
    text = re.sub('’', '\'', text)
    text = re.sub('~|&nbsp;|\xa0|\u200b', ' ', text)
    text = re.sub('&quot;', '"', text)
    
    if normalize_cn_punct:
        # Standardize Chinese punctuations
        # (necessary for sentence tokenization, useful for translation)
        text = re.sub('。|\|', '. ', text)
        text = re.sub('，|、', ', ', text)
        text = re.sub('！', '! ', text)
        text = re.sub('？', '? ', text)
        text = re.sub('：', ': ', text)
        text = re.sub('；', '; ', text)
        text = re.sub('（', ' (', text)
        text = re.sub('）', ') ', text)
        text = re.sub('—+', ' - ', text)
        text = re.sub('《|》|〈|〉|“|”|「|」|﹁|﹂|【|】|&quot;', '"', text)
    
    # Sometimes the spaces surrounding "()" are omitted
    text = re.sub('\(', ' (', text)
    text = re.sub('\)', ') ', text)
        
    # Only keep the line breaks if the text is in Chinese
    # because sometimes Chinese texts use line breaks to indicate sentence segmentation
    # (otherwise just replace them with white spaces later)
    if re.search('[\u4e00-\u9fff]+', text):
        text = re.sub('\s*[\n\r]+\s*', ' ' + line_break_replacement + ' ', text)
    
    # Clean HTML tags
    text = html_text.extract_text(text)
    text = re.sub('\s*[\n\r]+\s*', ' ' + line_break_replacement + ' ', text)
    
    # Remove URLs
    # (for translation purposes since it's not necessary to translate URLs)
    if normalize_url:
        text = re.sub('\(*\s*http\S+|\S+\.com\S*', '', text)
    
    # Strip extra white spaces
    text = re.sub('\s+', ' ', text)
    text = text.strip()
    
    # The following cleanings are more aggressive and are hence case-specific
    if remove_punctuations:
        text = text.translate(text.maketrans('', '', string.punctuation))
    
    if remove_spaces:
        text = re.sub(' ', '', text)
    
    if lower:
        text = text.lower()
    
    return text


def tokenize_sents(text, line_break_replacement='[EOL]'):
    # First pass using NLTK's `sent_tokenize`
    sents = sent_tokenize(text)
    
    # Second pass to split on line breaks
    sents = [sent.split(line_break_replacement) for sent in sents]
    
    # Concatenate into a single list
    sents = list(itertools.chain(*sents))
    sents = [sent.strip() for sent in sents if sent.strip()]
    
    # De-dupe while preserving the order
    # https://www.peterbe.com/plog/fastest-way-to-uniquify-a-list-in-python-3.6
    return list(dict.fromkeys(sents))


def remove_duplicate_summaries(summaries, titles, dedupe_within_summaries=False, need_sent_tokenization=True, line_break_replacement='[EOL]'):
    # First, split descriptions into sentences (if needed)
    if need_sent_tokenization:
        summaries = [tokenize_sents(text, line_break_replacement) for text in summaries]

    # Concatenate all descriptions into one list
    if dedupe_within_summaries:
        all_sents = list(itertools.chain(*(summaries + titles)))
    else:
        all_sents = list(itertools.chain(*titles))

    # For de-duping purposes, remove white spaces and punctuations
    all_sents = [clean_text(sent, remove_punctuations=True, remove_spaces=True, lower=True) for sent in all_sents]

    # Find the duplicate sentences
    if dedupe_within_summaries:
        sent_freq = pd.Series(all_sents).value_counts()
        dupe_sent = sent_freq[sent_freq > 1].index
    else:
        dupe_sent = all_sents

    # Remove duplicate sentences from each episode description
    summaries = [[
        sent for sent in summary if clean_text(sent, remove_punctuations=True, remove_spaces=True, lower=True) not in dupe_sent
    ] for summary in summaries]

    return summaries