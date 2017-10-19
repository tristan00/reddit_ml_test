import numpy as np
import pandas as pd
import sqlite3
import time
from nltk.tokenize import sent_tokenize, word_tokenize
import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data

test_size = 20000

def word_count(str):
    return len(word_tokenize(str.lower()))

def sentence_count(str):
    return len(sent_tokenize(str.lower()))

def get_percentile(num):
    global upvote_list
    upvote_list.sort()
    for i in upvote_list:
        if i >= num:
            return (upvote_list.index(i) + 1)/len(upvote_list)
    return 0

def upvote_classification(upvotes):
    rank = get_percentile(upvotes)
    if rank < .1:
        return 1
    if rank < .2:
        return 2
    if rank < .3:
        return 3
    if rank < .4:
        return 4
    if rank < .5:
        return 5
    if rank < .6:
        return 6
    if rank < .7:
        return 7
    if rank < .8:
        return 8
    if rank < .9:
        return 9
    else:
        return 10


def upvote_classification(upvotes):
    rank = get_percentile(upvotes)
    if rank < .1:
        return 1
    if rank < .2:
        return 2
    if rank < .3:
        return 3
    if rank < .4:
        return 4
    if rank < .5:
        return 5
    if rank < .6:
        return 6
    if rank < .7:
        return 7
    if rank < .8:
        return 8
    if rank < .9:
        return 9
    else:
        return 10

# Load data
conn = sqlite3.connect('reddit.db')

subs = {}
for count, i in enumerate(list(conn.execute('select distinct subreddit from posts ').fetchall())):
    subs[i[0]] = count

print(subs)

inputs = list(conn.execute('select c.text, c.upvotes, p.subreddit from comment c  join posts p on c.post_id = p.post_id').fetchall())


upvote_list=[]
input_list = []
for count, i in enumerate(inputs):
    upvote_list.append(i[1])
    input_list.append({'text': i[0], 'upvotes' : i[1], 'subreddit':subs[i[2]]})

df = pd.DataFrame.from_dict(input_list)

conn.close()
print(df.head())

df['word_count'] = df['text'].apply(word_count)
df['sentence_count'] = df['text'].apply(sentence_count)
df['classification'] = df['upvotes'].apply(upvote_classification)

df.drop(['text', 'upvotes'], axis=1)
inputX = df.loc[:, ['word_count', 'subreddit']].as_matrix()
inputY = df.loc[:, ['classification']].as_matrix()

print(inputY)

learning_rate = .01
training_epoch = test_size
display_step= 1000
n_samples = inputY.size

x = tf.placeholder(tf.float32, [None, 2])
w = tf.Variable(tf.zeros([2,2]))

b = tf.Variable(tf.zeros([2]))
y_values = tf.add(tf.matmul(x, w), b)
y = tf.nn.softmax(y_values)
y_ = tf.placeholder(tf.float32, [None,2])

cost = tf.reduce_sum(tf.pow(y_ - y, 2))/(2*n_samples)
optimizer = tf.train.GradientDescentOptimizer(learning_rate).minimize(cost)
init = tf.initialize_all_variables()
sess = tf.Session(config=tf.ConfigProto(log_device_placement=True))
sess.run(init)

for i in range(training_epoch):
    sess.run(optimizer, feed_dict={x: inputX, y_: inputY})

    if (i) % display_step == 0:
        cc = sess.run(cost, feed_dict={x: inputX, y_:inputY})
        print("Training step:", '%04d' % (i), "cost=", "{:.9f}".format(cc))

print("Optimization Finished!")
training_cost = sess.run(cost, feed_dict={x: inputX, y_: inputY})
print("Training cost=", training_cost, "W=", sess.run(w), "b=", sess.run(b), '\n')

# Create model
#stolen from https://github.com/aymericdamien/TensorFlow-Examples/blob/master/examples/3_NeuralNetworks/multilayer_perceptron.py
#def multilayer_perceptron(x):
#    # Hidden fully connected layer with 256 neurons
#    layer_1 = tf.add(tf.matmul(x, weights['h1']), biases['b1'])
#    # Hidden fully connected layer with 256 neurons
#    layer_2 = tf.add(tf.matmul(layer_1, weights['h2']), biases['b2'])
#    # Output fully connected layer with a neuron for each class
#    out_layer = tf.matmul(layer_2, weights['out']) + biases['out']
#    return out_layer