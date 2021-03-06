
import torch
import torchvision

from albumentations.pytorch import ToTensor
from albumentations import Normalize, HorizontalFlip, Compose

import numpy as np

class album_transform:
    def __init__(self,flag):
        self.traintransform = Compose([HorizontalFlip(),Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),ToTensor()])
        self.testtransform = Compose([Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),ToTensor()])
        self.flag = flag
    
    def __call__(self,img):
        img = np.array(img)
        if self.flag == "train":
            img = self.traintransform(image = img)['image']
        else:
            img = self.testtransform(image = img)['image']
        return img

def Get_Cifar():
    
    traintransform = album_transform("train")
    testtransform = album_transform("test")
    
    trainset = torchvision.datasets.CIFAR10(root='./data', train=True,download=True, transform=traintransform)
    
    testset = torchvision.datasets.CIFAR10(root='./data', train=False,download=True, transform=testtransform)
    
    return trainset,testset


def DataLoader(train_set,test_set,cuda_batch_size,SEED):
    
    cuda = torch.cuda.is_available()
    if cuda:
        torch.cuda.manual_seed(SEED)

    # dataloader arguments - something you'll fetch these from cmdprmt
    dataloader_args = dict(shuffle=True, batch_size=128, num_workers=4, pin_memory=True) if cuda else dict(shuffle=True, batch_size=64)
    
    # train dataloader
    train_loader = torch.utils.data.DataLoader(train_set, **dataloader_args)
    
    # test dataloader
    test_loader = torch.utils.data.DataLoader(test_set, **dataloader_args)

    return train_loader, test_loader

def get_device():
    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    return device
