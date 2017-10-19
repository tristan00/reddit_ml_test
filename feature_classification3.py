from nltk.tokenize import sent_tokenize, word_tokenize
import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data
import sqlite3
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import random
import pickle
from collections import Counter

hm_lines = 100000

stop = set(stopwords.words('english'))
stop.update(['.', ',', '"', "'", '?', '!', ':', ';', '(', ')', '[', ']', '{', '}'])

upvote_list1 = []
upvote_list2 = []


def word_count(str):
    return len(word_tokenize(str.lower()))

def sentence_count(str):
    return len(sent_tokenize(str.lower()))

def get_percentile(num, parent):
    if parent:
        upvote_list = upvote_list1
    else:
        upvote_list = upvote_list2
    upvote_list.sort()
    for i in upvote_list:
        if i >= num:
            return (upvote_list.index(i) + 1)/len(upvote_list)
    return 0

def upvote_classification(upvotes, parent):
    rank = get_percentile(upvotes, parent)
    if rank < .2:
        return [1, 0, 0, 0, 0]
    if rank < .4:
        return [0, 1, 0, 0, 0]
    if rank < .6:
        return [0, 0, 1, 0, 0]
    if rank < .8:
        return [0, 0, 0, 1, 0]
    else:
        return [0, 0, 0, 0, 1]

def get_data():
    global upvote_list1
    global upvote_list2
    conn = sqlite3.connect('reddit.db')
    subs = {}
    for count, i in enumerate(list(conn.execute('select distinct subreddit from posts ').fetchall())):
        subs[i[0]] = count
    inputs = list(conn.execute('select c1.text, c1.upvotes, c2.text, c2.upvotes, p.subreddit from comment c1 join comment c2 on c1.comment_id = c2.parent_id  join posts p on c1.post_id = p.post_id').fetchall())

    print("num of comments: ", len(inputs))
    full_text_parent = ""
    full_text_child = ""

    for i in inputs:
        upvote_list1.append(i[1])
        upvote_list2.append(i[3])
        temp_child = i[1]
        temp_parent = i[3]
        for j in stop:
            temp_child.replace(j, '')
            temp_parent.replace(j, '')
        full_text_parent += (temp_parent + ' ')
        full_text_child += (temp_child + ' ')

    fdist_parent = nltk.FreqDist(word_tokenize(full_text_parent))
    fdist_child = nltk.FreqDist(word_tokenize(full_text_child))

    parent_most_common_words = list(fdist_parent.most_common(50))
    child_most_common_words = list(fdist_child.most_common(50))

    feature_set = []
    #upvote buckets child, upvote buckets parent,  then child words, then parent words, 110 length
    for i in inputs:
        temp_array = []
        temp_array.extend(upvote_classification(i[3], False))
        temp_array.extend(upvote_classification(i[1], True))

        for j in child_most_common_words:
            if j in i[2]:
                temp_array.append(1)
            else:
                temp_array.append(0)

        for j in parent_most_common_words:
            if j in i[2]:
                temp_array.append(1)
            else:
                temp_array.append(0)
        feature_set.append([temp_array, temp_array.extend(upvote_classification(i[3], False))])
    return feature_set

def create_feature_sets_and_labels(test_size = .1)
    lexicon = get_data()
    random.shuffle(lexicon)
    


#TODO: figure out how to pull reddit data
mnist = input_data.read_data_sets("tmp/data/", one_hot=True)

hot_array = []
n_nodes_hl1 = 500
n_nodes_hl2 = 500
n_nodes_hl3 = 500
n_classes = 10
batch_size = 100

#TODO: figure out modify for reddit data
x = tf.placeholder('float', [None, 784])
y = tf.placeholder('float')

def neural_network_model(data):
    hidden_1_layer = {'weights': tf.Variable(tf.random_normal([784, n_nodes_hl1])),
                      'biases': tf.Variable(tf.random_normal([n_nodes_hl1]))}
    hidden_2_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl1, n_nodes_hl2])),
                      'biases': tf.Variable(tf.random_normal([n_nodes_hl2]))}
    hidden_3_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl2, n_nodes_hl3])),
                      'biases': tf.Variable(tf.random_normal([n_nodes_hl3]))}
    output_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl3, n_classes])),
                  'biases': tf.Variable(tf.random_normal([n_classes]))}

    l1 = tf.add(tf.matmul(data, hidden_1_layer['weights']), hidden_1_layer['biases'])
    l1 = tf.nn.relu(l1)

    l2 = tf.add(tf.matmul(l1, hidden_2_layer['weights']), hidden_2_layer['biases'])
    l2 = tf.nn.relu(l2)

    l3 = tf.add(tf.matmul(l2, hidden_3_layer['weights']), hidden_3_layer['biases'])
    l3 = tf.nn.relu(l3)

    output = tf.add(tf.matmul(l3, output_layer['weights']),  output_layer['biases'])
    return output

def train_neural_network(x):
    prediction = neural_network_model(x)
    cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=prediction, labels=y))
    optimizer = tf.train.AdamOptimizer().minimize(cost)

    hm_epochs = 20
    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())

        for epoch in range(hm_epochs):
            epoch_loss = 0
            for _ in range(int(mnist.train.num_examples/batch_size)):
                epoch_x, epoch_y = mnist.train.next_batch(batch_size)
                _, c = sess.run([optimizer, cost], feed_dict= {x:epoch_x, y:epoch_y})
                epoch_loss += c
            print("Epoch", epoch, 'completed out of', hm_epochs, 'loss:', epoch_loss)

        correct = tf.equal(tf.argmax(prediction, 1), tf.argmax(y, 1))
        accuracy = tf.reduce_mean(tf.cast(correct, 'float'))
        print('Accuracy:', accuracy.eval({x:mnist.test.images, y:mnist.test.labels}))



train_neural_network(x)