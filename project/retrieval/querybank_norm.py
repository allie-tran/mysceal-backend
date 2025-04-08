import json

import numpy as np
from configs import DATA_DIRECTORY
from query_parse.types.requests import Data
from query_parse.visual import blurred_indices, siglip_model


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


# Load training queries
query_features = np.load(f"{DATA_DIRECTORY}/query_features.npy")


# Precompute once for all test queries
beta = 20
k = 10000


# Step 1: Precompute with training queries and dataset features
def precompute(data: Data):
    train_test = (
        query_features @ siglip_model.norm_photo_features[data].T
    )  # shape: (N, I)
    train_test_exp = np.exp(train_test * beta)
    retrieved_videos = get_retrieved_videos(train_test_exp, k)
    normalizing_sum = np.sum(a=train_test_exp, axis=0)
    return retrieved_videos, normalizing_sum


precomputed = {data: precompute(data) for data in siglip_model.norm_photo_features}


def apply_qb_norm_to_query(
    test_query_feat, features, retrieved_videos, normalizing_sum, beta
):
    test_test = test_query_feat @ features.T  # shape: (1, I)
    test_test = test_test.reshape(1, -1)
    test_test_exp = np.exp(test_test * beta)
    test_test_normalized = test_test_exp.copy()
    index_for_normalizing = get_index_to_normalize(test_test_exp, retrieved_videos)
    test_test_normalized[index_for_normalizing, :] = (
        test_test_exp[index_for_normalizing, :] / normalizing_sum
    )
    return test_test_normalized


def get_similarities(data, encoded_query, filters=[]):
    features = siglip_model.norm_photo_features[data]
    retrieved_videos, normalizing_sum = precomputed[data]

    sim = apply_qb_norm_to_query(
        encoded_query, features, retrieved_videos, normalizing_sum, beta
    )
    sim = sim.reshape(-1)
    sim[blurred_indices[data]] = -1e10
    if filters:
        sim[filters] = -1e10
    return sim


def get_normed_similarity(data, encoded_query, filters=[]):
    features = siglip_model.norm_photo_features[data]
    retrieved_videos, normalizing_sum = precomputed[data]

    normed_sim = apply_qb_norm_to_query(
        encoded_query, features, retrieved_videos, normalizing_sum, beta
    )
    normed_sim = normed_sim.reshape(-1)
    normed_sim[blurred_indices[data]] = -1e10
    if filters:
        normed_sim[filters] = -1e10
    return normed_sim


def load_segments(data):
    try:
        photo_ids = siglip_model.photo_ids[data]
        segments = json.load(open(f"{DATA_DIRECTORY}/segments.json"))
        segment_photos = []
        for start, end in segments:
            segment_photos.append(photo_ids[start:end])
        return segments, segment_photos
    except:
        return [], []


presegments = {data: load_segments(data) for data in siglip_model.norm_photo_features}


def get_segments(top_photos, photo_ids, segments, blurred):
    done = set()
    found_segments = []
    for photo_id in top_photos:
        if photo_id in done:
            continue
        # get the segment for the photo_id
        index = np.where(photo_ids == photo_id)[0][0]
        segment = []
        for start, end in segments:
            if index >= start and index < end:
                segment = [i for i in range(start, end) if i not in blurred]
                segment = [photo_ids[i] for i in segment]
                done.update(segment)
                break
        if len(segment) == 0:
            continue
        found_segments.append(segment)
    return found_segments
