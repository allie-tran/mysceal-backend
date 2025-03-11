import os

import cupy as cp
import numpy as np
import rmm
from pylibraft.common import DeviceResources
from pylibraft.neighbors import ivf_flat
from rmm.allocators.cupy import rmm_cupy_allocator

from query_parse.types.requests import Data
from query_parse.visual import ClipModel, clip_model, clipa_model

mr = rmm.mr.PoolMemoryResource(rmm.mr.CudaMemoryResource(), initial_pool_size=2**15)
rmm.mr.set_current_device_resource(mr)
cp.cuda.set_allocator(rmm_cupy_allocator)
handle = DeviceResources()

def make_ivf_flat():
    index_params = ivf_flat.IndexParams(
        n_lists=1024,  # Number of lists
        metric="inner_product",  # Distance metric
        add_data_on_build=True,  # Add the data to the index when building
        kmeans_n_iters=25,  # Number of iterations for k-means
    )
    search_params = ivf_flat.SearchParams(n_probes=64)
    return index_params, search_params


def build_index(model: ClipModel, data: Data):
    index_params, search_params = make_ivf_flat()
    print(f"Building index for {model.name} {data}")
    vectors = cp.asarray(model.norm_photo_features[data], dtype=np.float32)
    index = ivf_flat.build(index_params, vectors, handle=handle)
    handle.sync()
    ivf_flat.save(os.path.join("cachedir", f"{model.name}_{data}.index"), index)
    print(f"Index built for {model.name} {data}")
    return index, search_params

REBUILD = True
def load_index(model: ClipModel, data: Data):
    path = os.path.join("cachedir", f"{model.name}_{data}.index")
    if os.path.exists(path) and not REBUILD:
        index = ivf_flat.load(path)
        handle.sync()
        return index, ivf_flat.SearchParams(n_probes=64)
    else:
        return build_index(model, data)

# INDICES = {
#     "clip": {
#         Data.Deakin: None,
#         Data.LSC23: load_index(clip_model, Data.LSC23),
#     },
#     "clipa": {
#         Data.Deakin: load_index(clipa_model, Data.Deakin),
#         Data.LSC23: None,
#     }
# }

# Function to perform a search
def search(model: ClipModel, data: Data, query_vector: np.ndarray, top_k: int):
    """ Returns an approximation of the scores """
    index, search_params = load_index(model, data)
    query_vector = cp.asarray(query_vector, dtype=np.float32)
    handle = DeviceResources()
    distances, indices = ivf_flat.search(
        search_params, index, query_vector, k=top_k, handle=handle
    )
    handle.sync()
    score_arrays = np.ones(len(model.photo_ids[data]), dtype=np.float32)
    score_arrays[indices] = 1 - distances
    return score_arrays

# search(clipa_model, Data.Deakin, clipa_model.norm_photo_features[Data.Deakin][0], 10)
# search(clip_model, Data.LSC23, clip_model.norm_photo_features[Data.LSC23][0], 10)

