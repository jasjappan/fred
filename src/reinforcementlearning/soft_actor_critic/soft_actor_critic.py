from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import time

import imageio
import tensorflow as tf
from absl import logging
from tf_agents.drivers import dynamic_step_driver
from tf_agents.environments import suite_gym
from tf_agents.environments import tf_py_environment
from tf_agents.eval import metric_utils
from tf_agents.metrics import py_metrics
from tf_agents.metrics import tf_metrics
from tf_agents.metrics import tf_py_metric
from tf_agents.policies import greedy_policy
from tf_agents.policies import random_tf_policy
from tf_agents.replay_buffers import tf_uniform_replay_buffer
from tf_agents.utils import common

# PYTHONUNBUFFERED=1;LD_LIBRARY_PATH=/usr/local/cuda-10.0/lib64
from src.reinforcementlearning.soft_actor_critic.sac_utils import create_agent


def show_progress(agent, env):
    time_step = env.reset()
    steps = 0
    while not time_step.is_last() and steps < 400:
        action_step = agent.policy.action(time_step)
        time_step = env.step(action_step.action)
        env.render()
        steps += 1


tf.compat.v1.enable_v2_behavior()
logging.set_verbosity(logging.INFO)

print("GPU Available: ", tf.test.is_gpu_available())

print("eager is on: {}".format(tf.executing_eagerly()))

env_name = 'BipedalWalkerHardcore-v2'
num_iterations = 100000
actor_fc_layers = (256, 256)
critic_obs_fc_layers = None
critic_action_fc_layers = None
critic_joint_fc_layers = (256, 256)
# Params for collect
initial_collect_steps = 10000
collect_steps_per_iteration = 1
replay_buffer_capacity = 1000000
# Params for target update
target_update_tau = 0.005
target_update_period = 1
# Params for train
train_steps_per_iteration = 1
batch_size = 256
actor_learning_rate = 3e-4
critic_learning_rate = 3e-4
alpha_learning_rate = 3e-4
td_errors_loss_fn = tf.compat.v1.losses.mean_squared_error
gamma = 0.99
reward_scale_factor = 1.0
gradient_clipping = None
use_tf_functions = True
# Params for eval
num_eval_episodes = 1
eval_interval = 2500
# Params for summaries and logging
train_checkpoint_interval = 5000
policy_checkpoint_interval = 5000
rb_checkpoint_interval = 50000
log_interval = 1000
summary_interval = 1000
summaries_flush_secs = 10
debug_summaries = False
summarize_grads_and_vars = False
eval_metrics_callback = None

root_dir = os.path.expanduser('/home/thomas/PycharmProjects/test')
train_dir = os.path.join(root_dir, 'train')
eval_dir = os.path.join(root_dir, 'eval')

train_summary_writer = tf.compat.v2.summary.create_file_writer(
    train_dir, flush_millis=summaries_flush_secs * 1000)
train_summary_writer.set_as_default()

eval_summary_writer = tf.compat.v2.summary.create_file_writer(
    eval_dir, flush_millis=summaries_flush_secs * 1000)
eval_metrics = [
    tf_metrics.AverageReturnMetric(buffer_size=num_eval_episodes),
    tf_metrics.AverageEpisodeLengthMetric(buffer_size=num_eval_episodes)
]

global_step = tf.compat.v1.train.get_or_create_global_step()
with tf.compat.v2.summary.record_if(
        lambda: tf.math.equal(global_step % summary_interval, 0)):

    # tf_env = tf_py_environment.TFPyEnvironment(suite_gym.wrap_env(BipedalWalker2(), max_episode_steps=1600))
    tf_env = tf_py_environment.TFPyEnvironment(suite_gym.load(env_name))
    eval_tf_env = tf_py_environment.TFPyEnvironment(suite_gym.load(env_name))

    time_step_spec = tf_env.time_step_spec()
    observation_spec = time_step_spec.observation
    action_spec = tf_env.action_spec()

    tf_agent = create_agent(time_step_spec, observation_spec, action_spec, global_step,
                            actor_fc_layers=actor_fc_layers,
                            critic_obs_fc_layers=critic_obs_fc_layers,
                            critic_action_fc_layers=critic_action_fc_layers,
                            critic_joint_fc_layers=critic_joint_fc_layers,
                            target_update_tau=target_update_tau,
                            target_update_period=target_update_period,
                            actor_learning_rate=actor_learning_rate,
                            critic_learning_rate=critic_learning_rate,
                            alpha_learning_rate=alpha_learning_rate,
                            td_errors_loss_fn=td_errors_loss_fn,
                            gamma=gamma,
                            reward_scale_factor=reward_scale_factor,
                            gradient_clipping=gradient_clipping,
                            debug_summaries=debug_summaries,
                            summarize_grads_and_vars=summarize_grads_and_vars)

    # Make the replay buffer.
    replay_buffer = tf_uniform_replay_buffer.TFUniformReplayBuffer(
        data_spec=tf_agent.collect_data_spec,
        batch_size=1,
        max_length=replay_buffer_capacity)
    replay_observer = [replay_buffer.add_batch]

    train_metrics = [
        tf_metrics.NumberOfEpisodes(),
        tf_metrics.EnvironmentSteps(),
        tf_py_metric.TFPyMetric(py_metrics.AverageReturnMetric()),
        tf_py_metric.TFPyMetric(py_metrics.AverageEpisodeLengthMetric()),
    ]

    eval_policy = greedy_policy.GreedyPolicy(tf_agent.policy)
    initial_collect_policy = random_tf_policy.RandomTFPolicy(
        tf_env.time_step_spec(), tf_env.action_spec())
    collect_policy = tf_agent.collect_policy

    train_checkpointer = common.Checkpointer(
        ckpt_dir=train_dir,
        agent=tf_agent,
        global_step=global_step,
        metrics=metric_utils.MetricsGroup(train_metrics, 'train_metrics'))
    policy_checkpointer = common.Checkpointer(
        ckpt_dir=os.path.join(train_dir, 'policy'),
        policy=eval_policy,
        global_step=global_step)
    rb_checkpointer = common.Checkpointer(
        ckpt_dir=os.path.join(train_dir, 'replay_buffer'),
        max_to_keep=1,
        replay_buffer=replay_buffer)

    train_checkpointer.initialize_or_restore()
    rb_checkpointer.initialize_or_restore()

    eval_py_env = suite_gym.load(env_name)

    show_progress(tf_agent, eval_py_env)

    initial_collect_driver = dynamic_step_driver.DynamicStepDriver(
        tf_env,
        initial_collect_policy,
        observers=replay_observer,
        num_steps=initial_collect_steps)

    collect_driver = dynamic_step_driver.DynamicStepDriver(
        tf_env,
        collect_policy,
        observers=replay_observer + train_metrics,
        num_steps=collect_steps_per_iteration)

    if use_tf_functions:
        initial_collect_driver.run = common.function(initial_collect_driver.run)
        collect_driver.run = common.function(collect_driver.run)
        tf_agent.train = common.function(tf_agent.train)

    # Collect initial replay data.
    logging.info(
        'Initializing replay buffer by collecting experience for %d steps with '
        'a random policy.', initial_collect_steps)
    initial_collect_driver.run()

    results = metric_utils.eager_compute(
        eval_metrics,
        eval_tf_env,
        eval_policy,
        num_episodes=num_eval_episodes,
        train_step=global_step,
        summary_writer=eval_summary_writer,
        summary_prefix='Metrics',
    )
    metric_utils.log_metrics(eval_metrics)

    time_step = None
    policy_state = collect_policy.get_initial_state(tf_env.batch_size)

    timed_at_step = global_step.numpy()
    time_acc = 0

    # Dataset generates trajectories with shape [Bx2x...]
    dataset = replay_buffer.as_dataset(
        num_parallel_calls=3,
        sample_batch_size=batch_size,
        num_steps=2).prefetch(3)
    iterator = iter(dataset)


    def train_step():
        experience, _ = next(iterator)
        return tf_agent.train(experience)


    if use_tf_functions:
        train_step = common.function(train_step)

    time_before_training = time.time()

    for iteration in range(num_iterations):
        start_time = time.time()
        time_step, policy_state = collect_driver.run(
            time_step=time_step,
            policy_state=policy_state,
        )
        for _ in range(train_steps_per_iteration):
            train_loss = train_step()
        time_acc += time.time() - start_time

        if global_step.numpy() % log_interval == 0:
            logging.info('step = %d, loss = %f', global_step.numpy(),
                         train_loss.loss)
            steps_per_sec = (global_step.numpy() - timed_at_step) / time_acc
            logging.info('%.3f steps/sec', steps_per_sec)
            tf.compat.v2.summary.scalar(
                name='global_steps_per_sec', data=steps_per_sec, step=global_step)
            timed_at_step = global_step.numpy()
            time_acc = 0

        for train_metric in train_metrics:
            train_metric.tf_summaries(
                train_step=global_step, step_metrics=train_metrics[:2])

        if global_step.numpy() % eval_interval == 0:
            results = metric_utils.eager_compute(
                eval_metrics,
                eval_tf_env,
                eval_policy,
                num_episodes=num_eval_episodes,
                train_step=global_step,
                summary_writer=eval_summary_writer,
                summary_prefix='Metrics',
            )
            metric_utils.log_metrics(eval_metrics)

            print("current itteration: {}".format(iteration))

        global_step_val = global_step.numpy()
        if global_step_val % train_checkpoint_interval == 0:
            train_checkpointer.save(global_step=global_step_val)

        if global_step_val % policy_checkpoint_interval == 0:
            policy_checkpointer.save(global_step=global_step_val)

        if global_step_val % rb_checkpoint_interval == 0:
            rb_checkpointer.save(global_step=global_step_val)

    time_after_trianing = time.time()

    elapsed_time = time_after_trianing - time_before_training
    print(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))

eval_py_env = suite_gym.load(env_name)
num_episodes = 3
video_filename = 'test.mp4'
with imageio.get_writer(video_filename, fps=60) as video:
    for _ in range(num_episodes):
        time_step = eval_py_env.reset()
        video.append_data(eval_py_env.render())
        while not time_step.is_last():
            action_step = tf_agent.policy.action(time_step)
            time_step = eval_py_env.step(action_step.action)
            video.append_data(eval_py_env.render())