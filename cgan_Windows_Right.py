import argparse
import os
import sys

sys.path.append("../Dataset")
from matlab_dataset import MatLabDataset
from json_dataset import JSONDataset
import numpy as np

from torchvision.utils import save_image
import torchvision.transforms as transforms

from torch.autograd import Variable

import torch.nn as nn
import torch

os.makedirs("images", exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument(
    "--n_epochs", type=int, default=20, help="number of epochs of training"
)
parser.add_argument(
    "--batch_size",
    type=int,
    default=64,
    help="size of the batches")
parser.add_argument(
    "--lr",
    type=float,
    default=0.0002,
    help="adam: learning rate")
parser.add_argument(
    "--b1",
    type=float,
    default=0.5,
    help="adam: decay of first order momentum of gradient",
)
parser.add_argument(
    "--b2",
    type=float,
    default=0.999,
    help="adam: decay of first order momentum of gradient",
)
parser.add_argument(
    "--n_cpu",
    type=int,
    default=8,
    help="number of cpu threads to use during batch generation",
)
parser.add_argument(
    "--features",
    type=int,
    default=800,
    help="number of features")
parser.add_argument("--latent_dim", type=int, default=100,
                    help="dimensionality of the latent space")
parser.add_argument(
    "--n_classes", type=int, default=10, help="number of classes for dataset"
)
parser.add_argument(
    "--sample_interval",
    type=int,
    default=100,
    help="interval between image sampling")
opt = parser.parse_args()
print(opt)

cuda = True if torch.cuda.is_available() else False


class Generator(nn.Module):
    def __init__(self):
        super(Generator, self).__init__()

        self.label_emb = nn.Embedding(opt.n_classes, opt.n_classes)

        def block(in_feat, out_feat, normalize=True):
            layers = [nn.Linear(in_feat, out_feat)]
            if normalize:
                layers.append(nn.BatchNorm1d(out_feat, 0.8))
            layers.append(nn.LeakyReLU(0.2, inplace=True))
            return layers

        self.model = nn.Sequential(
            *block(opt.latent_dim + opt.n_classes, 128, normalize=False),
            *block(128, 256),
            *block(256, 512),
            *block(512, 1024),
            nn.Linear(1024, int(opt.features)),
            nn.Tanh()
        )

    def forward(self, noise, labels):
        # Concatenate label embedding and image to produce input
        gen_input = torch.cat((self.label_emb(labels), noise), -1)
        img = self.model(gen_input)
        img = img.view(img.size(0), opt.features)
        return img


class Discriminator(nn.Module):
    def __init__(self):
        super(Discriminator, self).__init__()

        self.label_embedding = nn.Embedding(opt.n_classes, opt.n_classes)

        self.model = nn.Sequential(
            nn.Linear(opt.n_classes + int(opt.features), 512),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(512, 512),
            nn.Dropout(0.4),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(512, 512),
            nn.Dropout(0.4),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(512, 1),
        )

    def forward(self, img, labels):
        # Concatenate label embedding and image to produce input
        print("img - - (forward) :    ")
        print(img.size())
        print("labels - - (forward) :    ")
        print(labels.size())
        print("self.label_embedding(labels):   ")
        print(self.label_embedding(labels).size())

        d_in = torch.cat((img.view(img.size(0), -1),
                          self.label_embedding(labels)), -1)
        print("d_in:   ")
        print(d_in.size())
        validity = self.model(d_in)
        print("validity:   ")
        print(validity.size())
        return validity


# Loss functions
adversarial_loss = torch.nn.MSELoss()

# Initialize generator and discriminator
generator = Generator()
discriminator = Discriminator()

if cuda:
    generator.cuda()
    discriminator.cuda()
    adversarial_loss.cuda()

# Configure data loader
dataset_dir = os.path.join(os.getcwd(), "../Dataset")
dataloader = torch.utils.data.DataLoader(
    #MatLabDataset(
        #os.path.join(dataset_dir, "OfficeCaltech_1_SourceData.mat"),
        #os.path.join(dataset_dir, "OfficeCaltech_1_SourceLabel.mat"),
    #),
    JSONDataset(os.path.join(dataset_dir, "OfficeCaltech_1_SourceData.mat.json"),os.path.join(dataset_dir,"OfficeCaltech_1_SourceLabel.mat.json"),),
    #JSONDataset(os.path.join(dataset_dir, "OfficeCaltech_1_SourceData.mat.json"),),
    #JSONDataset(os.path.join(dataset_dir, "OfficeCaltech_1_SourceLabel.mat.json"),),
    batch_size=opt.batch_size,
    shuffle=True,
)

# Optimizers
optimizer_G = torch.optim.Adam(
    generator.parameters(), lr=opt.lr, betas=(opt.b1, opt.b2)
)
optimizer_D = torch.optim.Adam(
    discriminator.parameters(), lr=opt.lr, betas=(opt.b1, opt.b2)
)

FloatTensor = torch.cuda.FloatTensor if cuda else torch.FloatTensor
LongTensor = torch.cuda.LongTensor if cuda else torch.LongTensor


def sample_image(n_row, batches_done):
    """Saves a grid of generated digits ranging from 0 to n_classes"""
    # Sample noise
    z = Variable(
        FloatTensor(
            np.random.normal(
                0, 1, (n_row ** 2, opt.latent_dim))))
    # Get labels ranging from 0 to n_classes for n rows
    labels = np.array([num for _ in range(n_row) for num in range(n_row)])
    labels = Variable(LongTensor(labels))
    gen_imgs = generator(z, labels)
    save_image(
        gen_imgs.data,
        "images/%d.png" %
        batches_done,
        nrow=n_row,
        normalize=True)


# ----------
#  Training
# ----------

for epoch in range(opt.n_epochs):
    for i, (imgs, labels) in enumerate(dataloader):
        batch_size = imgs.shape[0]
        print("labels   - - (enumerate(dataloader))  :  ")
        print(labels.size())
        print("Length of labels:   ")
        print(len(labels))
        tt=len(labels)
        print("Length = :")
        print(tt)

        # Adversarial ground truths
        valid = Variable(
            FloatTensor(
                batch_size,
                1).fill_(1.0),
            requires_grad=False)
        fake = Variable(
            FloatTensor(
                batch_size,
                1).fill_(0.0),
            requires_grad=False)

        # Configure input
        real_imgs = Variable(imgs.type(FloatTensor))
        labels = Variable(labels.type(LongTensor))

        # -----------------
        #  Train Generator
        # -----------------

        optimizer_G.zero_grad()

        # Sample noise and labels as generator input
        z = Variable(
            FloatTensor(
                np.random.normal(
                    0, 1, (batch_size, opt.latent_dim))))
        gen_labels = Variable(
            LongTensor(np.random.randint(0, opt.n_classes, batch_size))
        )

        # Generate a batch of images
        gen_imgs = generator(z, gen_labels)

        # Loss measures generator's ability to fool the discriminator
        print("labels  (before view)   :   ")
        print(labels.size())
        # labels=labels.view(64)
        labels = labels.view(tt)
        print("labels  (after view)   :   ")
        print(labels.size())

        validity = discriminator(gen_imgs, gen_labels)
        g_loss = adversarial_loss(validity, valid)

        g_loss.backward()
        optimizer_G.step()

        # ---------------------
        #  Train Discriminator
        # ---------------------

        optimizer_D.zero_grad()

        # Loss for real images
        validity_real = discriminator(real_imgs, labels)
        d_real_loss = adversarial_loss(validity_real, valid)

        # Loss for fake images
        validity_fake = discriminator(gen_imgs.detach(), gen_labels)
        d_fake_loss = adversarial_loss(validity_fake, fake)

        # Total discriminator loss
        d_loss = (d_real_loss + d_fake_loss) / 2

        d_loss.backward()
        optimizer_D.step()

        print(
            "[Epoch %d/%d] [Batch %d/%d] [D loss: %f] [G loss: %f]" %
            (epoch, opt.n_epochs, i, len(dataloader), d_loss.item(), g_loss.item()))

        batches_done = epoch * len(dataloader) + i
        if batches_done % opt.sample_interval == 0:
            sample_image(n_row=10, batches_done=batches_done)
