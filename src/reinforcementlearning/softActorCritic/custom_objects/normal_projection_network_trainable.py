from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
import tensorflow_probability as tfp
from tf_agents.distributions import utils as distribution_utils
from tf_agents.networks import network
from tf_agents.networks import utils as network_utils
from tf_agents.specs import distribution_spec
from tf_agents.specs import tensor_spec


def tanh_squash_to_spec(inputs, spec):
    """Maps inputs with arbitrary range to range defined by spec using `tanh`."""
    means = (spec.maximum + spec.minimum) / 2.0
    magnitudes = (spec.maximum - spec.minimum) / 2.0

    return means + magnitudes * tf.tanh(inputs)


class NormalProjectionNetworkTrainable(network.DistributionNetwork):

    def __init__(self,
                 sample_spec,
                 activation_fn=None,
                 init_means_output_factor=0.01,
                 init_stds_output_factor=0.5,
                 std_bias_initializer_value=0.0,
                 mean_transform=tanh_squash_to_spec,
                 std_transform=tf.nn.softplus,
                 scale_distribution=False,
                 name='NormalProjectionNetwork'):
        """Creates an instance of NormalProjectionNetwork.

        Args:
          sample_spec: A `tensor_spec.BoundedTensorSpec` detailing the shape and
            dtypes of samples pulled from the output distribution.
          activation_fn: Activation function to use in dense layer.
          init_means_output_factor: Output factor for initializing action means
            weights.
          std_bias_initializer_value: Initial value for the bias of the
            stddev_projection_layer or the direct bias_layer depending on the
            state_dependent_std flag.
          mean_transform: Transform to apply to the calculated means. Uses
            `tanh_squash_to_spec` by default.
          std_transform: Transform to apply to the stddevs.
          state_dependent_std: If true, stddevs will be produced by MLP from state.
            else, stddevs will be an independent variable.
          scale_distribution: Whether or not to use a bijector chain to scale
            distributions to match the sample spec. Note the TransformedDistribution
            does not support certain operations required by some agents or policies
            such as KL divergence calculations or Mode.
          name: A string representing name of the network.
        """
        if len(tf.nest.flatten(sample_spec)) != 1:
            raise ValueError('Normal Projection network only supports single spec '
                             'samples.')
        self._scale_distribution = scale_distribution
        output_spec = self._output_distribution_spec(sample_spec, name)
        super(NormalProjectionNetworkTrainable, self).__init__(
            # We don't need these, but base class requires them.
            input_tensor_spec=None,
            state_spec=(),
            output_spec=output_spec,
            name=name)

        self._sample_spec = sample_spec
        self._mean_transform = mean_transform
        self._std_transform = std_transform

        self._means_projection_layer = tf.keras.layers.Dense(
            sample_spec.shape.num_elements(),
            activation=activation_fn,
            kernel_initializer=tf.compat.v1.keras.initializers.VarianceScaling(
                scale=init_means_output_factor),
            bias_initializer=tf.keras.initializers.Zeros(),
            name='means_projection_layer')

        self._stddev_projection_layer = tf.keras.layers.Dense(
            sample_spec.shape.num_elements(),
            activation=activation_fn,
            kernel_initializer=tf.compat.v1.keras.initializers.VarianceScaling(
                scale=init_stds_output_factor),
            bias_initializer=tf.keras.initializers.Constant(
                value=std_bias_initializer_value),
            name='stddev_projection_layer')

    def _output_distribution_spec(self, sample_spec, network_name):
        input_param_shapes = tfp.distributions.Normal.param_static_shapes(
            sample_spec.shape)

        input_param_spec = {
            name: tensor_spec.TensorSpec(
                shape=shape,
                dtype=sample_spec.dtype,
                name=network_name + '_' + name)
            for name, shape in input_param_shapes.items()
        }

        def distribution_builder(*args, **kwargs):
            distribution = tfp.distributions.Normal(*args, **kwargs)
            if self._scale_distribution:
                return distribution_utils.scale_distribution_to_spec(
                    distribution, sample_spec)
            return distribution

        return distribution_spec.DistributionSpec(
            distribution_builder, input_param_spec, sample_spec=sample_spec)

    def call(self, inputs, outer_rank, training=False, mask=None):
        if inputs.dtype != self._sample_spec.dtype:
            raise ValueError(
                'Inputs to NormalProjectionNetwork must match the sample_spec.dtype.')

        if mask is not None:
            raise NotImplementedError(
                'NormalProjectionNetwork does not yet implement action masking; got '
                'mask={}'.format(mask))

        # outer_rank is needed because the projection is not done on the raw
        # observations so getting the outer rank is hard as there is no spec to
        # compare to.
        batch_squash = network_utils.BatchSquash(outer_rank)
        inputs = batch_squash.flatten(inputs)

        means = self._means_projection_layer(inputs, training=training)
        means = tf.reshape(means, [-1] + self._sample_spec.shape.as_list())

        # If scaling the distribution later, use a normalized mean.
        if not self._scale_distribution and self._mean_transform is not None:
            means = self._mean_transform(means, self._sample_spec)
        means = tf.cast(means, self._sample_spec.dtype)

        stds = self._stddev_projection_layer(inputs, training=training)

        if self._std_transform is not None:
            stds = self._std_transform(stds)
        stds = tf.cast(stds, self._sample_spec.dtype)

        means = batch_squash.unflatten(means)
        stds = batch_squash.unflatten(stds)

        return self.output_spec.build_distribution(loc=means, scale=stds), ()

    def call_raw(self, inputs, outer_rank, training=False, mask=None):
        if inputs.dtype != self._sample_spec.dtype:
            raise ValueError(
                'Inputs to NormalProjectionNetwork must match the sample_spec.dtype.')

        if mask is not None:
            raise NotImplementedError(
                'NormalProjectionNetwork does not yet implement action masking; got '
                'mask={}'.format(mask))

        # outer_rank is needed because the projection is not done on the raw
        # observations so getting the outer rank is hard as there is no spec to
        # compare to.
        batch_squash = network_utils.BatchSquash(outer_rank)
        inputs = batch_squash.flatten(inputs)

        means = self._means_projection_layer(inputs, training=training)
        means = tf.reshape(means, [-1] + self._sample_spec.shape.as_list())

        # If scaling the distribution later, use a normalized mean.
        if not self._scale_distribution and self._mean_transform is not None:
            means = self._mean_transform(means, self._sample_spec)
        means = tf.cast(means, self._sample_spec.dtype)

        stds = self._stddev_projection_layer(inputs, training=training)

        if self._std_transform is not None:
            stds = self._std_transform(stds)
        stds = tf.cast(stds, self._sample_spec.dtype)

        means = batch_squash.unflatten(means)
        stds = batch_squash.unflatten(stds)

        return means, stds