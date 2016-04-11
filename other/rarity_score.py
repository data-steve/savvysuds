from __future__ import division

import matplotlib.pyplot as plt
import pandas as pd
import process_data as get
from scipy import stats


FTISO_PATH = '../data/input/ftiso.csv'
BEERS_PATH = '../data/input/beers.csv'
BREWERIES_PATH = '../data/input/breweries.csv'
DISTRIBUTION_PATH = '../data/input/beer_distribution.csv'
SCORE_WEIGHTS = {
    'ratio_score': 0.4,
    'iso_score': 0.4,
    'untappd_score': 0.1,
    'geo_score': 0.05,
    'production_score': 0.05
    }

def weighted_percentile(vector):
    """returns percentile values of a vector
    calculates the percentile of each element of data, with duplicate
    values set to the mean of the chunk of the distribution they occupy
    http://stackoverflow.com/questions/12414043/map-each-list-value-to-its-corresponding-percentile
    """
    return stats.rankdata(vector, method='average') / len(vector)


def feature_scale(vector):
    """returns values scaled to 0-1 range as pandas series
    not used
    """
    score_diff = vector - vector.min()
    norm_score = score_diff / (vector.max() - vector.min())
    return norm_score


def wishlist_scores(data_path, scoring_function):
    '''returns iso/ft ratio score & iso count ratio score as dataframes
    see weighted_percentile for methodology
    higher ratio or iso count means higher score
    '''
    # load data, then calculate iso & ft counts
    ftiso = pd.read_csv(data_path)
    iso = ftiso[ftiso['type'] == 'iso']
    iso = iso.groupby('beer_id', as_index=False).count()
    ft = ftiso[ftiso['type'] == 'ft']
    ft = ft.groupby('beer_id', as_index=False).count()
    # get ratio score
    iso_ft = pd.merge(iso, ft, on=['beer_id'])
    iso_ft['ratio'] = iso_ft['id_x'] / iso_ft['id_y']
    iso_ft['ratio_score'] = scoring_function(iso_ft['ratio'])
    # get iso score
    iso['iso_score'] = scoring_function(iso['id'])
    return iso_ft, iso


def distribution_scores(data_path, scoring_function):
    """returns distribution scores as dataframe
    scores calculated based on how number of states fall
    distributing to fewer states results in a higher score
    does more to punish broadly distributed beers than reward limited releases
    """
    distribution = pd.read_csv(data_path)
    distribution['states'] = distribution \
        .drop(['brewery_id', 'Name'], axis=1) \
        .apply(lambda x: (x != 'N').sum(), axis=1)
    distribution['geo_score'] = scoring_function(distribution['states'])
    # inverts distribution scores to punish higher geographic footprint
    distribution['geo_score'] = 1 - distribution['geo_score']
    return distribution


def production_scores(data_path, scoring_function):
    """scores breweries based on production
    higher production results in a lower score
    weighted_percentile returns uniform distribution, vs skewed original spread
    """
    breweries = pd.read_csv(data_path)
    breweries['production_score'] = scoring_function(
        breweries['beer_count']
        )
    # inverts distribution scores to punish higher production
    breweries['production_score'] = 1 - breweries['production_score']
    return breweries


def untappd_scores(data_path, scoring_function):
    """scores beers based on untappd ratings
    weighted percentile results in uniform distribution
    """
    beers = pd.read_csv(data_path)
    beers['untappd_score'] = scoring_function(beers['score'])
    return beers


def agg_weighted_score(rarity, score_weights, drop_nas=True, filter_zeros=True):
    """returns beer name, id, & score based on the inputed weights
    input - weights as a dictionary
    output - weighted valuation
    """
    rarity['score'] = 0
    if drop_nas:
        before = len(rarity)
        rarity = rarity.dropna()
        after = len(rarity)
        print 'dropped ' + str(after - before) + ' na rows'
    if filter_zeros:
        before = len(rarity)
        for column in ['iso_score']:
            rarity = rarity[rarity[column] != 0]
        after = len(rarity)
        print 'dropped ' + str(after - before) + ' zero rows'
        print str(after) + ' rows remain'
    for category, weight in score_weights.iteritems():
        rarity['score'] += rarity[category] * weight
    rarity['score'] = rarity['score'] / sum(score_weights.values())
    return rarity


def main():
    """returns a dataframe with scores from 0-1 based on iso count, ft/iso,
    distribution, production, and untappd ratings
    note that all hardcodes at beginning of file flow here
    """
    beers = pd.read_csv(BEERS_PATH)
    # initialize output dataframe
    rarity = beers[['name', 'id', 'brewery_id']]
    # fix column names to prevent redundancies during the merges
    rarity.columns = ['name', 'beer', 'brewery']
    # get all scores based on inputted method (feature scale or percentile)
    ft, iso = wishlist_scores(FTISO_PATH, feature_scale)
    distribution = distribution_scores(DISTRIBUTION_PATH, weighted_percentile)
    breweries = production_scores(BREWERIES_PATH, weighted_percentile)
    beers = untappd_scores(BEERS_PATH, weighted_percentile)
    # merge all dfs
    beer_scores = [
        (iso_ft[['beer_id', 'ratio_score']], 'beer'),
        (iso[['beer_id', 'iso_score']], 'beer'),
        (beers[['id', 'untappd_score']], 'beer'),
        (distribution[['brewery_id', 'geo_score']], 'brewery'),
        (breweries[['id', 'production_score']], 'brewery')
        ]
    for df, rarity_idx in beer_scores:
        rarity = rarity.merge(df, how='left', left_on=rarity_idx,
            right_on=df.columns[0]).drop(df.columns[0], axis=1)
    agg_rarity = agg_weighted_score(rarity, SCORE_WEIGHTS)
    return agg_rarity


if __name__ == '__main__':
    beers = pd.read_csv(BEERS_PATH)
    # initialize output dataframe
    rarity = beers[['name', 'id', 'brewery_id']]
    # fix column names to prevent redundancies during the merges
    rarity.columns = ['name', 'beer', 'brewery']
    # get all scores based on inputted method (feature scale or percentile)
    iso_ft, iso = wishlist_scores(FTISO_PATH, weighted_percentile)
    distribution = distribution_scores(DISTRIBUTION_PATH, feature_scale)
    breweries = production_scores(BREWERIES_PATH, feature_scale)
    beers = untappd_scores(BEERS_PATH, feature_scale)
    # merge all dfs
    beer_scores = [
        (iso_ft[['beer_id', 'ratio_score']], 'beer'),
        (iso[['beer_id', 'iso_score']], 'beer'),
        (beers[['id', 'untappd_score']], 'beer'),
        (distribution[['brewery_id', 'geo_score']], 'brewery'),
        (breweries[['id', 'production_score']], 'brewery')
        ]
    for df, rarity_idx in beer_scores:
        rarity = rarity.merge(df, how='left', left_on=rarity_idx,
            right_on=df.columns[0]).drop(df.columns[0], axis=1)
    agg_rarity = agg_weighted_score(rarity, SCORE_WEIGHTS, drop_nas=True)
