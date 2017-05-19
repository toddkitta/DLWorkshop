# Import the relevant components
from __future__ import print_function # Use a function definition from future version (say 3.x from 2.7 interpreter)
import numpy as np
import sys
import os
import cntk as C
import time
from cntk.logging.progress_print import ProgressPrinter

#C.device.try_set_default_device(C.device.cpu())
C.device.try_set_default_device(C.device.gpu(0))

# Ensure we always get the same amount of randomness
np.random.seed(0)

# Read a CTF formatted text (as mentioned above) using the CTF deserializer from a file
def create_reader(path, is_training, input_dim, num_label_classes):
    labelStream = C.io.StreamDef(field='labels', shape=num_label_classes, is_sparse=False)
    featureStream = C.io.StreamDef(field='features', shape=input_dim, is_sparse=False)
    deserializer = C.io.CTFDeserializer(path, C.io.StreamDefs(labels = labelStream, features = featureStream))
    return C.io.MinibatchSource(deserializer,
       randomize = is_training, max_sweeps = C.io.INFINITELY_REPEAT if is_training else 1)

# Evaluate the model using a given test file
def evaluate_model(model, features, labels, test_file):
    reader = create_reader(test_file, False, features.shape[0], labels.shape[0])
    evaluator = C.Evaluator(C.classification_error(model, labels))
    test_input_map = {
       features : reader.streams.features,
       labels: reader.streams.labels
    }
    
    minibatch_size = 2000
    test_result = 0.0
    num_minibatches = 0
    data = reader.next_minibatch(minibatch_size, input_map = input_map)
    while bool(data):
        test_result = test_result + evaluator.test_minibatch(data)
        num_minibatches += 1
        data = reader.next_minibatch(minibatch_size, input_map = input_map)
    return None if num_minibatches == 0 else test_result*100 / num_minibatches

# Define a computational network for multi-class logistic regression
def create_mlr_model(features, output_dim):
    input_dim = features.shape[0]
    weight_param = C.parameter(shape=(input_dim, output_dim))
    bias_param = C.parameter(shape=(output_dim))
    return C.times(features, weight_param) + bias_param

# Define the data dimensions
input_dim = 784
num_output_classes = 10

# Define features and labels
features = C.input(input_dim)
labels = C.input(num_output_classes)

# Scale the input to 0-1 range by dividing each pixel by 255.
z = create_mlr_model(features/255.0, num_output_classes)

# Define loss and error functions
loss = C.cross_entropy_with_softmax(z, labels)
error = C.classification_error(z, labels)

# Instantiate the trainer object to drive the model training
learning_rate = 0.2
lr_schedule = C.learning_rate_schedule(learning_rate, C.UnitType.minibatch)
learner = C.sgd(z.parameters, lr_schedule)
progress_printer = ProgressPrinter(500)
trainer = C.Trainer(z, (loss, error), [learner], [progress_printer])

# Initialize the parameters for the trainer
minibatch_size = 64
num_samples_per_sweep = 50000
num_sweeps_to_train_with = 10
num_minibatches_to_train = (num_samples_per_sweep * num_sweeps_to_train_with) / minibatch_size

# Create the reader to training data set
train_file = "../../Data/MNIST_train.txt"
reader_train = create_reader(train_file, True, input_dim, num_output_classes)

# Map the data streams to the input and labels.
input_map = {
    labels  : reader_train.streams.labels,
    features  : reader_train.streams.features
} 

# Run the trainer on and perform model training
start_time = time.time()
for i in range(0, int(num_minibatches_to_train)):
    data = reader_train.next_minibatch(minibatch_size, input_map = input_map)
    trainer.train_minibatch(data)

print(time.time() - start_time)


# Evaluate the model
validation_file = "../../Data/MNIST_validate.txt"

error_rate = evaluate_model(z, features, labels, validation_file)
print("Average validation error: {0:.2f}%".format(error_rate))

test_file = '../../Data/MNIST_test.txt'
error_rate = evaluate_model(z, features, labels, test_file)
print("Average test error: {0:.2f}%".format(error_rate))


