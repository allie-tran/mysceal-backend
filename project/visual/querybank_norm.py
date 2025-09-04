import numpy as np
from retrieval.async_utils import timer
from visual.types import Array1D


# Returns list of retrieved top k videos based on the sims matrix
def get_retrieved_videos(sims, k):
    argm = np.argsort(-sims, axis=1)
    topk = argm[:, :k].reshape(-1)
    retrieved_videos = np.unique(topk)
    return retrieved_videos


# Returns list of indices to normalize from sims based on videos
def get_index_to_normalize(sims, videos):
    argm = np.argsort(-sims, axis=1)[:, 0]
    result = np.array(list(map(lambda x: x in videos, argm)))
    result = np.nonzero(result)
    return result


@timer("apply_qb_norm")
def apply_qb_norm_to_query(
    test_query_feat, features, retrieved_videos, normalizing_sum, beta
) -> Array1D[np.float32]:
    test_test = test_query_feat @ features.T  # shape: (1, I)
    test_test = test_test.reshape(1, -1)
    test_test_exp = np.exp(test_test * beta)
    test_test_normalized = test_test_exp.copy()
    index_for_normalizing = get_index_to_normalize(test_test_exp, retrieved_videos)
    test_test_normalized[index_for_normalizing, :] = (
        test_test_exp[index_for_normalizing, :] / normalizing_sum
    )
    test_test_normalized = test_test_normalized.reshape(-1).astype(np.float32)
    return test_test_normalized
