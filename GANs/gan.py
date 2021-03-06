import argparse
import os
import sys

sys.path.append("../Dataset")
from matlab_dataset import MatLabDataset
from json_dataset import JSONDataset

import numpy as np
import torch.nn as nn
import torch
import torchvision.transforms as transforms
from torchvision.utils import save_image

from torch.autograd import Variable


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
parser.add_argument("--latent_dim", type=int, default=100,
                    help="dimensionality of the latent space")
parser.add_argument(
    "--features",
    type=int,
    default=800,
    help="number of features")
parser.add_argument(
    "--sample_interval",
    type=int,
    default=400,
    help="interval betwen image samples")
opt = parser.parse_args()
print(opt)

cuda = torch.cuda.is_available()


class Generator(nn.Module):
    def __init__(self):
        super(Generator, self).__init__()

        def block(in_feat, out_feat, normalize=True):
            layers = [nn.Linear(in_feat, out_feat)]
            if normalize:
                layers.append(nn.BatchNorm1d(out_feat, 0.8))
            layers.append(nn.LeakyReLU(0.2, inplace=True))
            return layers

        self.model = nn.Sequential(
            *block(opt.latent_dim, 128, normalize=False),
            *block(128, 256),
            *block(256, 512),
            *block(512, 1024),
            nn.Linear(1024, int(opt.features)),
            nn.Tanh()
        )

    def forward(self, z):
        img = self.model(z)
        img = img.view(img.size(0), opt.features)
        return img


class Discriminator(nn.Module):
    def __init__(self):
        super(Discriminator, self).__init__()

        self.model = nn.Sequential(
            nn.Linear(int(opt.features), 512),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(512, 256),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(256, 1),
            nn.Sigmoid(),
        )

    def forward(self, img):
        img_flat = img.view(img.size(0), -1)  # img_flat: torch.Size([64, 784])
        validity = self.model(img_flat)  # validity: torch.Size([64, 1])

        return validity


# Loss function
adversarial_loss = torch.nn.BCELoss()

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
    # MatLabDataset( os.path.join(dataset_dir, "OfficeCaltech_1_SourceData.mat"), os.path.join(dataset_dir, "OfficeCaltech_1_SourceLabel.mat"),),
    JSONDataset(
        os.path.join(dataset_dir, "OfficeCaltech_1_SourceData.mat.json"),
        os.path.join(dataset_dir, "OfficeCaltech_1_SourceLabel.mat.json"),
    ),
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

Tensor = torch.cuda.FloatTensor if cuda else torch.FloatTensor

# ----------
#  Training
# ----------

result = []
for epoch in range(opt.n_epochs):
    for i, (imgs, _) in enumerate(
        dataloader
    ):  # imgs : torch.Size([64,1,28,28])  #len(dataloader):938

        # Adversarial ground truths
        valid = Variable(
            Tensor(imgs.size(0), 1).fill_(1.0), requires_grad=False
        )  # valid: torch.Size([64,1])
        fake = Variable(
            Tensor(imgs.size(0), 1).fill_(0.0), requires_grad=False
        )  # fake:  torch.Size([64,1])

        # Configure input
        # real_imgs: torch.Size([64,1,28,28])
        real_imgs = Variable(imgs.type(Tensor))

        # -----------------
        #  Train Generator
        # -----------------

        optimizer_G.zero_grad()

        # Sample noise as generator input
        z = Variable(
            Tensor(np.random.normal(0, 1, (imgs.shape[0], opt.latent_dim)))
        )  # z: torch.Size([64*100])

        # Generate a batch of images
        gen_imgs = generator(z)  # gen_imgs.size() : torch.Size([64,1,28,28])

        # Loss measures generator's ability to fool the discriminator
        g_loss = adversarial_loss(discriminator(gen_imgs), valid)

        g_loss.backward()
        optimizer_G.step()

        # ---------------------
        #  Train Discriminator
        # ---------------------

        optimizer_D.zero_grad()

        # Measure discriminator's ability to classify real from generated
        # samples
        real_loss = adversarial_loss(discriminator(real_imgs), valid)
        fake_loss = adversarial_loss(discriminator(gen_imgs.detach()), fake)
        d_loss = (real_loss + fake_loss) / 2

        d_loss.backward()
        optimizer_D.step()

        print(
            "[Epoch %d/%d] [Batch %d/%d] [D loss: %f] [G loss: %f]"
            % (
                epoch,
                opt.n_epochs,
                i,
                len(dataloader),
                d_loss.item(),
                g_loss.item(),
            )  # len(dataloader):938
        )

        batches_done = epoch * len(dataloader) + i
        if batches_done % opt.sample_interval == 0:
            result.append(gen_imgs[0])
result_tensor = torch.stack(result)
result_numpy = result_tensor.numpy()
