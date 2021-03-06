
import cv2
import numpy as np
import torch
from torchvision import models, transforms
from torch.autograd import Variable
import torch
import torch.nn as nn
import torch.nn.functional as F
import pickle
import os
import argparse
import matplotlib.pyplot as plt
from matplotlib import cm
import PIL


class CamExtractor():
    """
        Extracts cam features from the model
    """

    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None

    def save_gradient(self, grad):
        self.gradients = grad

    def forward_pass_on_convolutions(self, x):
        """
            Does a forward pass on convolutions, hooks the function at given layer
        """
        conv_output = None
        for module_name, module in self.model._modules.items():
            # print(module_name)
            if module_name == 'linear':
                return conv_output, x
            x = module(x)  # Forward
            #print(module_name, module)
            if module_name == self.target_layer:
                # print('True')
                # print(module_name)
                # print(x.shape)
                x.register_hook(self.save_gradient)
                conv_output = x  # Save the convolution output on that layer
        return conv_output, x

    def forward_pass(self, x):
        """
            Does a full forward pass on the model
        """
        
        # Forward pass on the convolutions
        conv_output, x = self.forward_pass_on_convolutions(x)
        print("In Forward pass")
        
        # Forward pass on the classifier
        x = F.avg_pool2d(x, 4)
        x = x.view(x.size(0), -1)
        # print(x.shape)
        x = self.model.linear(x)#self.linear(out
        return conv_output, x


class GradCam():
    """
        Produces class activation map
    """

    def __init__(self, model, target_layer):
        self.model = model
        self.model.eval()
        # Define extractor
        self.extractor = CamExtractor(self.model, target_layer)

    def generate_cam(self, input_image, target_index=None):
        # Full forward pass
        # conv_output is the output of convolutions at specified layer
        # model_output is the final output of the model (1, 1000)
        #cam = grad_cam.generate_cam(image_prep.to(device), 7)
        conv_output, model_output = self.extractor.forward_pass(input_image)

        model_output = model_output.to("cpu")
        conv_output = conv_output.to("cpu")
        #self.extractor = self.extractor.to("cpu")

        if target_index is None:
            target_index = np.argmax(model_output.data.numpy())
        # Target for backprop
        
        one_hot_output = torch.FloatTensor(1, model_output.size()[-1]).zero_() ##torch.
        one_hot_output[0][target_index] = 1
        # Zero grads
        self.model.linear.zero_grad()
        # self.model.classifier.zero_grad()
        # Backward pass with specified target
        model_output.backward(gradient=one_hot_output, retain_graph=True)
        # Get hooked gradients
        #guided_gradients = self.extractor.gradients.data.numpy()[0]
        guided_gradients = self.extractor.gradients.to("cpu").data.numpy()[0]
        # Get convolution outputs
        target = conv_output.data.numpy()[0]
        # Get weights from gradients
        # Take averages for each gradient
        weights = np.mean(guided_gradients, axis=(1, 2))
        # Create empty numpy array for cam
        cam = np.ones(target.shape[1:], dtype=np.float32)
        # Multiply each weight with its conv output and then, sum
        for i, w in enumerate(weights):
            cam += w * target[i, :, :]
        cam = cv2.resize(cam, (32, 32))
        cam = np.maximum(cam, 0)
        cam = (cam - np.min(cam)) / (np.max(cam) -
                                     np.min(cam))  # Normalize between 0-1
        cam = np.uint8(cam * 255)  # Scale between 0-255 to visualize
        return cam

def save_class_activation_on_image(org_img, activation_map, file_name):
    """
        Saves cam activation map and activation map on the original image
    Args:
        org_img (PIL img): Original image
        activation_map (numpy arr): activation map (grayscale) 0-255
        file_name (str): File name of the exported image
    """
    if not os.path.exists('./results'):
        os.makedirs('./results')
    # Grayscale activation map
    path_to_file = os.path.join('./results', file_name + '_Cam_Grayscale.jpg')
    cv2.imwrite(path_to_file, activation_map)
    # display(HTML('<h3>_Cam_Grayscale</h3>'))
    # show_img(activation_map)
    # Heatmap of activation map
    activation_heatmap = cv2.applyColorMap(activation_map, cv2.COLORMAP_HSV)
    path_to_file = os.path.join('./results', file_name + '_Cam_Heatmap.jpg')
    cv2.imwrite(path_to_file, activation_heatmap)
    # display(HTML('<h3>_Cam_Heatmap</h3>'))
    # show_img(activation_heatmap)
    # Heatmap on picture
    org_img = cv2.resize(org_img, (32, 32))
    img_with_heatmap = np.float32(activation_heatmap) + np.float32(org_img)
    img_with_heatmap = img_with_heatmap / np.max(img_with_heatmap)
    path_to_file = os.path.join('./results', file_name + '_Cam_On_Image.jpg')
    cv2.imwrite(path_to_file, np.uint8(255 * img_with_heatmap))
    img_with_heatmap = np.uint8(255 * img_with_heatmap)
    # display(HTML('<h3>_Cam_On_Image</h3>'))
    # show_img(img_with_heatmap)
    return activation_map, activation_heatmap, img_with_heatmap

def preprocess_image(cv2im, resize_im=False):
    """
        Processes image for CNNs
    Args:
        PIL_img (PIL_img): Image to process
        resize_im (bool): Resize to 224 or not
    returns:
        im_as_var (Pytorch variable): Variable that contains processed float tensor
    """
    img = np.float32(cv2.resize(cv2im, (32, 32))) / 255
    means = [0.5,0.5,0.5]   #[0.485, 0.456, 0.406]
    stds = [0.5,0.5,0.5]    #[0.229, 0.224, 0.225]

    preprocessed_img = img.copy()[:, :, ::-1]
    for i in range(3):
        preprocessed_img[:, :, i] = preprocessed_img[:, :, i] - means[i]
        preprocessed_img[:, :, i] = preprocessed_img[:, :, i] / stds[i]
    preprocessed_img = \
        np.ascontiguousarray(np.transpose(preprocessed_img, (2, 0, 1)))
    preprocessed_img = torch.from_numpy(preprocessed_img)
    preprocessed_img.unsqueeze_(0)
    input = preprocessed_img.requires_grad_(True)
    return input


def load_m(model_path,model_instance,target,export):    
    
    file_name_to_export = export
    target_class = int(target)

    model = model_instance
    model.load_state_dict(torch.load(model_path))

    num_ftrs = model.linear.in_features
    model.linear = nn.Linear(num_ftrs, 10)

    use_gpu = torch.cuda.is_available()
    #use_gpu = False

    if use_gpu:
        model = model.cuda()

    model.eval()

    return model
	
def get_CAMS(image_path,model_instance,model_path,target_class,tgt_layer,file_name):

    # Open CV preporcessing

    image = cv2.imread(image_path, 1)
    image.shape
    image_prep = preprocess_image(image)

    class_map = { 'airplane':0, 'automobile' : 1, 'bird' : 2, 'cat' : 3, 'deer' : 4,
    'dog': 5,'frog' : 6, 'horse' : 7, 'ship' : 8, 'truck' : 9 }
    
    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    
    # Load the model
    model = load_m(model_path,model_instance,class_map[target_class],"")#load_model()
    # Grad cam
    grad_cam = GradCam(model, target_layer=tgt_layer)
    # Generate cam mask
    cam = grad_cam.generate_cam(image_prep.to(device), 7)
    # Save mask
    activation_map, activation_heatmap, img_with_heatmap = save_class_activation_on_image(image, cam, file_name) 
    print('Grad cam completed')
    return activation_map, activation_heatmap, img_with_heatmap
