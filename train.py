# -*- coding: utf-8 -*-

from datetime import datetime
import time
import os
import tensorflow as tf
import numpy as np

import cnn
import util

FLAGS = tf.app.flags.FLAGS

tf.app.flags.DEFINE_string('data_dir', './data/ted500/', 'Directory of the data')
tf.app.flags.DEFINE_string('train_dir', './train/', 'Directory to save training checkpoint files')
tf.app.flags.DEFINE_integer('num_epoch', 50, 'Number of epochs to run')
tf.app.flags.DEFINE_boolean('use_pretrain', False, 'Use word2vec pretrained embeddings or not')
tf.app.flags.DEFINE_boolean('log_device_placement', False, 'Whether log device information in summary')

tf.app.flags.DEFINE_string('optimizer', 'adam', 'Optimizer to use. Must be one of "sgd", "adagrad", "adadelta" and "adam"')
tf.app.flags.DEFINE_float('init_lr', 0.01, 'Initial learning rate')
tf.app.flags.DEFINE_float('lr_decay', 0.95, 'LR decay rate')
tf.app.flags.DEFINE_integer('tolerance_step', 500, 'Decay the lr after loss remains unchanged for this number of steps')
tf.app.flags.DEFINE_float('dropout', 0.5, 'Dropout rate. 0 is no dropout.')

tf.app.flags.DEFINE_integer('log_step', 10, 'Write log to stdout after this step')
tf.app.flags.DEFINE_integer('summary_step', 200, 'Write summary after this step')
tf.app.flags.DEFINE_integer('save_epoch', 5, 'Save model after this epoch')

def train():
    # load data
    train_loader = util.DataLoader(os.path.join(FLAGS.data_dir, 'train.cPickle'), batch_size=FLAGS.batch_size)
    dev_loader = util.DataLoader(os.path.join(FLAGS.data_dir, 'test.cPickle'), batch_size=FLAGS.batch_size)
    max_steps = train_loader.num_batch * FLAGS.num_epoch # this is just an estimated number
    FLAGS.num_classes = train_loader.num_classes
    FLAGS.sent_len = train_loader.sent_len



    # train_dir
    timestamp = str(int(time.time()))
    out_dir = os.path.abspath(os.path.join(FLAGS.train_dir, timestamp))

    with tf.Graph().as_default():
        with tf.variable_scope('cnn', reuse=None):
            m = cnn.Model(FLAGS, is_train=True)
        with tf.variable_scope('cnn', reuse=True):
            mtest = cnn.Model(FLAGS, is_train=False)

        saver = tf.train.Saver(tf.all_variables())
        save_path = os.path.join(out_dir, 'model.ckpt')
        summary_op = tf.merge_all_summaries()

        sess = tf.Session(config=tf.ConfigProto(log_device_placement=FLAGS.log_device_placement))
        #summary_writer = tf.train.SummaryWriter(summary_dir, graph_def=sess.graph_def)
        summary_dir = os.path.join(out_dir, "summaries")
        summary_writer = tf.train.SummaryWriter(summary_dir, graph=sess.graph)
        sess.run(tf.initialize_all_variables())

        if FLAGS.use_pretrain:
            print "Use pretrained embeddings to initialize model ..."
            pretrained_embedding = np.load(os.path.join(FLAGS.data_dir, 'emb.npy'))
            m.assign_embedding(sess, pretrained_embedding)

        current_lr = FLAGS.init_lr
        lowest_loss_value = float("inf")
        step_loss_ascend = 0
        global_step = 0

        def dev_step(mtest, sess, data_loader):
            dev_loss = 0.0
            dev_accuracy = 0.0
            for _ in xrange(data_loader.num_batch):
                x_batch, y_batch = data_loader.next_batch()
                #x_batch = np.array(x_batch)
                loss_value, true_count = sess.run([mtest.total_loss, mtest.true_count_op],
                    feed_dict={mtest.inputs: x_batch, mtest.labels: y_batch})
                dev_loss += loss_value
                dev_accuracy += true_count
            dev_loss /= data_loader.num_batch
            dev_accuracy /= float(data_loader.num_batch * FLAGS.batch_size)
            data_loader.reset_pointer()
            return (dev_loss, dev_accuracy)

        # Note that this is a soft version of epoch.
        for epoch in range(FLAGS.num_epoch):
            train_loss = 0.0
            train_accuracy = 0.0
            train_loader.reset_pointer()
            for _ in xrange(train_loader.num_batch):
                m.assign_lr(sess, current_lr)
                global_step += 1
                start_time = time.time()
                x_batch, y_batch = train_loader.next_batch()
                feed = {m.inputs: x_batch, m.labels: y_batch}
                _, loss_value, true_count = sess.run([m.train_op, m.total_loss, m.true_count_op], feed_dict=feed)
                duration = time.time() - start_time
                train_loss += loss_value
                train_accuracy += true_count

                assert not np.isnan(loss_value), "Model loss is NaN."

                if global_step % FLAGS.log_step == 0:
                    examples_per_sec = FLAGS.batch_size / duration
                    accuracy = float(true_count) / FLAGS.batch_size
                    format_str = ('%s: step %d/%d (epoch %d/%d), acc = %.2f, loss = %.2f (%.1f examples/sec; %.3f sec/batch), lr: %.6f')
                    print (format_str % (datetime.now(), global_step, max_steps, epoch+1, FLAGS.num_epoch,
                                         accuracy, loss_value, examples_per_sec, duration, current_lr))

                    summary_writer.add_summary(_summary_for_scalar('train/loss', float(loss_value)), global_step=global_step)
                    summary_writer.add_summary(_summary_for_scalar('train/accuracy', float(accuracy)), global_step=global_step)

                if global_step % FLAGS.summary_step == 0:
                    summary_str = sess.run(summary_op)
                    summary_writer.add_summary(summary_str, global_step)

                # decay learning rate if necessary
                if loss_value < lowest_loss_value:
                    lowest_loss_value = loss_value
                    step_loss_ascend = 0
                else:
                    step_loss_ascend += 1
                if step_loss_ascend >= FLAGS.tolerance_step:
                    current_lr *= FLAGS.lr_decay
                    print '%s: step %d/%d (epoch %d/%d), LR decays to %.5f' % ((datetime.now(), global_step, max_steps, 
                        epoch+1, FLAGS.num_epoch, current_lr))
                    step_loss_ascend = 0

                # stop learning if learning rate is too low
                if current_lr < 1e-5: break

            # summary loss/accuracy after each epoch
            train_loss /= train_loader.num_batch
            train_accuracy /= float(train_loader.num_batch * FLAGS.batch_size)
            #summary_writer.add_summary(_summary_for_scalar('eval/train_loss', train_loss), global_step=epoch)
            #summary_writer.add_summary(_summary_for_scalar('eval/train_accuracy', train_accuracy), global_step=epoch)

            dev_loss, dev_accuracy = dev_step(mtest, sess, dev_loader)
            summary_writer.add_summary(_summary_for_scalar('dev/loss', dev_loss), global_step=global_step)
            summary_writer.add_summary(_summary_for_scalar('dev/accuracy', dev_accuracy), global_step=global_step)

            print("\nEpoch %d: train_loss = %.6f, train_accuracy = %.3f" % (epoch+1, train_loss, train_accuracy))
            print("Epoch %d: dev_loss = %.6f, dev_accuracy = %.3f\n" % (epoch+1, dev_loss, dev_accuracy))

            # save after fixed epoch
            if epoch % FLAGS.save_epoch == 0:
                saver.save(sess, save_path, global_step=epoch)
        saver.save(sess, save_path, global_step=epoch)

def _summary_for_scalar(name, value):
    return tf.Summary(value=[tf.Summary.Value(tag=name, simple_value=value)])

def main(argv=None):
    #if tf.gfile.Exists(FLAGS.train_dir):
    #    tf.gfile.DeleteRecursively(FLAGS.train_dir)
    #tf.gfile.MakeDirs(FLAGS.train_dir)
    if not tf.gfile.Exists(FLAGS.train_dir):
        tf.gfile.MakeDirs(FLAGS.train_dir)
    train()

if __name__ == '__main__':
    tf.app.run()