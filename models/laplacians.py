"""Functions related to getting the laplacian and the right number of pixels after pooling/unpooling.
"""

import numpy as np
import healpy as hp
from scipy import sparse
from scipy.sparse import coo_matrix
import torch

import sys

from pygsp.graphs.nngraphs.spherehealpix import SphereHealpix

# pylint: disable=W0223


def scipy_csr_to_sparse_tensor(csr_mat):
    """Convert scipy csr to sparse pytorch tensor.

    Args:
        csr_mat (csr_matrix): The sparse scipy matrix.

    Returns:
        sparse_tensor :obj:`torch.sparse.FloatTensor`: The sparse torch matrix.
    """
    coo = coo_matrix(csr_mat)
    values = coo.data
    indices = np.vstack((coo.row, coo.col))
    idx = torch.LongTensor(indices)
    vals = torch.FloatTensor(values)
    shape = coo.shape
    sparse_tensor = torch.sparse.FloatTensor(idx, vals, torch.Size(shape))
    sparse_tensor = sparse_tensor.coalesce()
    return sparse_tensor

def prepare_laplacian(laplacian):
    """Prepare a graph Laplacian to be fed to a graph convolutional layer.
    """

    def estimate_lmax(laplacian, tol=5e-3):
        """Estimate the largest eigenvalue of an operator.
        """
        lmax = sparse.linalg.eigsh(laplacian, k=1, tol=tol, ncv=min(laplacian.shape[0], 10), return_eigenvectors=False)
        lmax = lmax[0]
        lmax *= 1 + 2 * tol  # Be robust to errors.
        return lmax

    def scale_operator(L, lmax, scale=1):
        """Scale the eigenvalues from [0, lmax] to [-scale, scale].
        """
        I = sparse.identity(L.shape[0], format=L.format, dtype=L.dtype)
        L *= 2 * scale / lmax
        L -= I
        return L

    lmax = estimate_lmax(laplacian)
    laplacian = scale_operator(laplacian, lmax)
    laplacian = scipy_csr_to_sparse_tensor(laplacian)
    return laplacian

def get_healpix_laplacians(nside_list, laplacian_type="combinatorial", indexes_list=None, n_neighbours=8, nest=True):
    """Get the healpix laplacian list for a certain depth.
    Args:
        nodes (int): initial number of nodes.
        depth (int): the depth of the UNet.
        laplacian_type ["combinatorial", "normalized"]: the type of the laplacian.
    Returns:
        laps (list): increasing list of laplacians.
    """
    laps = []
    adjs = []

    if indexes_list is None:
        indexes_list = [None] * len(nside_list)

    for nside, indexes in zip(nside_list, indexes_list):
        G = SphereHealpix(subdivisions=nside, indexes=indexes, k=n_neighbours, nest=nest, lap_type=laplacian_type)
        G.compute_laplacian(laplacian_type)

        lap = prepare_laplacian(G.L)
        adj = scipy_csr_to_sparse_tensor(G.W)

        laps.append(lap)
        adjs.append(adj)

    return laps, adjs