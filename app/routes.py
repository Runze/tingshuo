
# coding: utf-8

from flask import render_template
from app import app, flatpages

import numpy as np
import pandas as pd
import pickle
import re
from collections import OrderedDict
from plotly.offline import plot
import plotly.graph_objs as go

@app.route('/')
@app.route('/index')
def index():
	return render_template('index.html')

# Podcast discovery
@app.route('/podcasts/')
def podcasts():
	# Visualize embeddings using plotly
	plot_div, js_callback = plot_podcast_embeddings(podcast_embeddings_2d)
	return render_template('podcasts.html', plot_div=plot_div, js_callback=js_callback, podcasts_per_country=podcasts_per_country)

# Podcast and country pages
# https://pythonspot.com/flask-with-static-html-files/
@app.route('/podcasts/<name>/')
def render_static(name):
	if name in podcast_id_to_episodes:
		podcast_id = name
		podcast = podcast_id_to_desc[podcast_id]
		episodes = podcast_id_to_episodes[podcast_id]
		phrase_count = podcast_id_to_phrase_count[podcast_id]
		return render_template('podcast.html', podcast=podcast, episodes=episodes, phrase_count=phrase_count)
	elif name in podcasts_per_country:
		podcasts = podcasts_per_country[name]
		return render_template('countries.html', podcasts=podcasts, podcast_id_to_phrase_count=podcast_id_to_phrase_count)
	else:
		return 'nothing selected'

# Blog posts
# http://www.jamesharding.ca/posts/simple-static-markdown-blog-in-flask/
POST_DIR = 'posts'

@app.route('/posts/')
def posts():
	posts = [p for p in flatpages if p.path.startswith(POST_DIR)]
	posts.sort(key=lambda item:item['date'], reverse=True)
	return render_template('posts.html', posts=posts)

@app.route('/posts/<name>/')
def post(name):
    path = '{}/{}'.format(POST_DIR, name)
    post = flatpages.get_or_404(path)
    return render_template('post.html', post=post)

# Podcast transcripts
TRANSCRIPT_DIR = 'transcripts'

@app.route('/transcripts/')
def transcripts():
	transcripts = [p for p in flatpages if p.path.startswith(TRANSCRIPT_DIR)]
	transcripts.sort(key=lambda item:item['date'], reverse=True)
	return render_template('transcripts.html', transcripts=transcripts)

@app.route('/transcripts/<name>/')
def transcript(name):
    path = '{}/{}'.format(TRANSCRIPT_DIR, name)
    transcript = flatpages.get_or_404(path)
    return render_template('transcript.html', transcript=transcript)

# About page
@app.route('/about/')
def about():
    post = flatpages.get_or_404('about')
    return render_template('about.html', post=post)

def plot_podcast_embeddings(podcast_embeddings_2d, top_n=30):
	# For visualization purposes, limit to top N podcasts per country
	podcast_embeddings_2d = podcast_embeddings_2d.groupby('country_fullname').head(top_n).copy()

	# Plot using Plotly
	traces = []
	countries = sorted(podcast_embeddings_2d['country_fullname'].unique())
	for country in countries:
	    podcast_embeddings_2d_curr = podcast_embeddings_2d[podcast_embeddings_2d['country_fullname'] == country]
	    
	    trace_curr = go.Scattergl(
	        x=podcast_embeddings_2d_curr['x'].tolist(),
	        y=podcast_embeddings_2d_curr['y'].tolist(),
	        mode='markers',
	        marker={'size': 12, 'opacity': .7},
	        name=country,
	        text=podcast_embeddings_2d_curr['hover_text'].tolist(),
	        customdata=list(zip(podcast_embeddings_2d_curr['podcast_id'], podcast_embeddings_2d_curr['artwork'])),
	        hoverinfo='text',
	        visible=True)
	    traces.append(trace_curr)
	layout = go.Layout(
	    hovermode='closest',
	    paper_bgcolor='rgba(0,0,0,0)',
	    plot_bgcolor='rgba(0,0,0,0)',
	    xaxis=dict(
	        showgrid=False,
	        zeroline=False,
	        showline=False,
	        ticks='',
	        showticklabels=False
	    ),
	    yaxis=dict(
	        showgrid=False,
	        zeroline=False,
	        showline=False,
	        ticks='',
	        showticklabels=False
	    ),
	    margin=dict(t=0, b=10))
	fig = go.Figure(data=traces, layout=layout)

	# Get HTML representation of plotly.js and this figure
	# https://community.plot.ly/t/hyperlink-to-markers-on-map/17858/6
	plot_div = plot(fig, output_type='div', include_plotlyjs=True)

	# Get id of html div element
	res = re.search('<div id="([^"]*)"', plot_div)
	div_id = res.groups()[0]
	mid_x = (podcast_embeddings_2d['x'].min() + podcast_embeddings_2d['x'].max()) / 2
	mid_y = (podcast_embeddings_2d['y'].min() + podcast_embeddings_2d['y'].max()) / 2
	
	# Build JavaScript callback for handling clicks and opening the URL in the trace's customdata 
	js_callback = """
		<script>
		var plot_element = document.getElementById("{div_id}");
		plot_element.on('plotly_click', function(data){{
		    var point = data.points[0];
		    if (point) {{
		        window.open(point.customdata[0]);
		    }}
		}})

		var hoverInfo = document.getElementById("hoverinfo");
		
		plot_element.on('plotly_hover', function(data){{
			var point = data.points[0];
		    hoverInfo.innerHTML = '<img src="' + point.customdata[1] + '" width="100%" height="100%">';
		    hoverInfo.classList.add('shadow');

		    if (point.x < {mid_x}) {{
		    	hoverInfo.style.right = "0%";
		    	hoverInfo.style.left = "60%";
		    }} else {{
		    	hoverInfo.style.left = "0%";
		    	hoverInfo.style.right = "60%";
		    }}
		    if (point.y < {mid_y}) {{
		    	hoverInfo.style.top = "60%";
		    	hoverInfo.style.bottom = "0%";
		    }} else {{
		    	hoverInfo.style.top = "0%";
		    	hoverInfo.style.bottom = "60%";
		    }}
		}})
		 .on('plotly_unhover', function(data){{
		    hoverInfo.innerHTML = '';
		    hoverInfo.classList.remove('shadow');
		}});
		</script>
	""".format(div_id=div_id, mid_x=mid_x, mid_y=mid_y)
	
	# Resize plot
	plot_div = re.sub('style="height: 100%; width: 100%;" class="plotly-graph-div"', 'class="plotly-graph-div plotly"', plot_div)

	return plot_div, js_callback

# Load podcast embeddings
podcast_embeddings_2d = pd.read_csv('app/static/podcast_embeddings_2d.csv', encoding='utf-8')

# Extract podcasts per country
podcasts_per_country = podcast_embeddings_2d.groupby('country_fullname').apply(lambda grp: grp.to_dict('records')).to_dict()
podcasts_per_country = OrderedDict(sorted(podcasts_per_country.items()))

# Remove translations for English podcasts
for podcasts in podcasts_per_country.values():
    for podcast in podcasts:
        if podcast['summary_label'] == podcast['summary_label_en_cleaned']:
            podcast.pop('summary_label_en_cleaned')

# Load podcast descriptions
podcast_id_to_desc = pickle.load(open('app/static/podcast_id_to_desc.pkl', 'rb'))

# Load episodes
podcast_id_to_episodes = pickle.load(open('app/static/podcast_id_to_episodes_cleaned.pkl', 'rb'))

# Load podcast noun phrase counts
podcast_id_to_phrase_count = pickle.load(open('app/static/podcast_id_to_phrase_count.pkl', 'rb'))