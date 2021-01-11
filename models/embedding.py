import torch
from torch import nn
import torch.nn.functional as F

from models.healpix_pool_unpool import Healpix
from models.laplacians import get_healpix_laplacians
from models.layers import SphericalChebBNPool

# pylint: disable=W0223


class SphericalGraphCNN(nn.Module):
    """Spherical GCNN Autoencoder.
    """

    def __init__(self, nside_list, indexes_list, kernel_size=4, laplacian_type="combinatorial", fc_dims=[[-1, 2048], [2048, 512], [512, 96]], n_aux_var=1):
        """Initialization.

        Args:
            kernel_size (int): chebychev polynomial degree
        """
        super().__init__()
        self.kernel_size = kernel_size
        self.pooling_class = Healpix(mode="max")

        self.n_aux_var = n_aux_var

        # Specify convolutional part

        self.laps = get_healpix_laplacians(nside_list=nside_list, laplacian_type=laplacian_type, indexes_list=indexes_list)
        self.cnn_layers = []

        for i, (in_ch, out_ch) in enumerate([(1, 32), (32, 64), (64, 128), (128, 256), (256, 256), (256, 256), (256, 256)]):
            layer = SphericalChebBNPool(in_ch, out_ch, self.laps[i], self.pooling_class.pooling, self.kernel_size)
            setattr(self, "layer_{}".format(i), layer)
            self.cnn_layers.append(layer)

        # Set shape of first input of FC layers to correspond to output of conv layers + aux variables
        fc_dims[0][0] = 256 + self.n_aux_var
        
        # Specify fully-connected part
        self.fc_layers = []
        for i, (in_ch, out_ch) in enumerate(fc_dims):
            layer = nn.Sequential(nn.Linear(in_ch, out_ch), nn.ReLU())
            setattr(self, "layer_fc_{}".format(i), layer)
            self.fc_layers.append(layer)

    def forward(self, x):
        """Forward Pass.

        Args:
            x (:obj:`torch.Tensor`): input to be forwarded.

        Returns:
            :obj:`torch.Tensor`: output
        """

        # Initialize tensor
        x = x.view(-1, 16384 + self.n_aux_var, 1)

        # Extract auxiliary variable
        x_aux = x[:, -self.n_aux_var:, :]
        x_aux = x_aux.view(-1, 1, self.n_aux_var)
        
        # Extract map to input into convolutional layers
        x = x[:, :-self.n_aux_var, :]

        # Convolutional layers
        for layer in self.cnn_layers:
            x = layer(x)

        # Concatenate auxiliary variable along last dimension
        x = torch.cat([x, x_aux], -1)

        # FC layers
        for layer in self.fc_layers:
            x = layer(x)

        # # FC layers
        # x = F.relu(self.fc1(x))
        # x = F.relu(self.fc2(x))

        return x[:, 0, :]
