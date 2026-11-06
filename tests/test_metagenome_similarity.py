import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api.metagenome_similarity import comparable_values  # noqa: E402


def _meta(**overrides):
    base = dict(
        acc='SRR1', biosample='SAMN1', model='NovaSeq', taxon_name='soil metagenome',
        spots=100, bases=5000, collection_date_parsed=None, published=None, geo_loc_name='Chile',
        biosample_attributes=[
            SimpleNamespace(k='depth_sam', v='5 m'),
            SimpleNamespace(k='primary_search', v='x'),
            SimpleNamespace(k='sample_name_sam', v='S1'),
        ])
    return SimpleNamespace(**{**base, **overrides})


def test_descriptive_columns_and_biosample_attributes_are_compared():
    values = comparable_values(_meta())
    assert values['model'] == 'NovaSeq'
    assert values['taxon_name'] == 'soil metagenome'
    assert values['depth'] == '5 m'  # _sam suffix stripped to match the displayed row key


def test_identifiers_and_per_run_measurements_are_compared_too():
    values = comparable_values(_meta())
    for key in ('biosample', 'spots', 'bases'):
        assert key in values
    assert 'primary_search' not in values


def test_collection_date_is_formatted_like_the_page():
    from datetime import datetime
    values = comparable_values(_meta(collection_date_parsed=datetime(2020, 3, 5)))
    assert values['collection_date_parsed'] == '5 March 2020'


def test_identifier_attributes_are_compared_too():
    attrs = [SimpleNamespace(k=k, v='x') for k in ('sample_accession', 'sample_alias', 'host')]
    assert set(comparable_values(_meta(biosample_attributes=attrs))) >= {'sample_accession', 'sample_alias', 'host'}


def test_placeholder_values_are_not_compared():
    attrs = [SimpleNamespace(k='depth_sam', v='missing'), SimpleNamespace(k='host_sam', v='Not Applicable'),
             SimpleNamespace(k='tissue', v='gut')]
    values = comparable_values(_meta(biosample_attributes=attrs, geo_loc_name='Not Provided'))
    assert 'depth' not in values and 'host' not in values and 'geo_loc_name' not in values
    assert values['tissue'] == 'gut'


def test_biosample_attribute_does_not_overwrite_a_column():
    attrs = [SimpleNamespace(k='geo_loc_name_sam', v='Peru')]
    assert comparable_values(_meta(geo_loc_name='Chile', biosample_attributes=attrs))['geo_loc_name'] == 'Chile'


def test_release_date_is_compared_like_the_page_shows_it():
    from datetime import datetime
    assert comparable_values(_meta(published=datetime(2021, 7, 1)))['releasedate'] == '1 July 2021'


def test_metalog_fields_are_compared_under_a_prefixed_key():
    from api.metagenome_similarity import metalog_comparable_values
    attributes = SimpleNamespace(metalog_rows=lambda: [{'k': 'Host', 'v': 'Sus scrofa'}, {'k': 'Diet', 'v': 'milk'}])
    assert metalog_comparable_values(attributes) == {'metalog:Host': 'Sus scrofa', 'metalog:Diet': 'milk'}


def test_run_without_metalog_data_has_no_metalog_values():
    from api.metagenome_similarity import metalog_comparable_values
    assert metalog_comparable_values(None) == {}


def test_identifiers_and_run_stamps_are_expected_to_differ():
    from api.metagenome_similarity import is_expected_to_differ
    for key in ('sample_name', 'biosample', 'bases', 'releasedate', 'experiment_title',
                'sample_accession', 'external_id', 'gold_id', 'ENA-FIRST-PUBLIC', 'ENA-LAST-UPDATE', 'INSDC-FIRST-PUBLIC', 'metalog:Couple id', 'metalog:Study code'):
        assert is_expected_to_differ(key), key


def test_informative_fields_are_not_expected_to_differ():
    from api.metagenome_similarity import is_expected_to_differ
    for key in ('depth', 'host', 'platform', 'model', 'geo_loc_name', 'collection_date_parsed',
                'metalog:Host', 'metalog:Diet', 'metalog:Age years'):
        assert not is_expected_to_differ(key), key


def test_attribute_identical_to_a_shown_column_row_is_already_shown():
    from api.metagenome_similarity import is_already_shown
    sections = [[{'raw_k': 'sample_name', 'v': 'Sample3_Uganda'}], [{'k': 'bases', 'v': 5}]]
    assert is_already_shown(sections, 'sample name', 'Sample3_Uganda')
    assert is_already_shown(sections, 'Sample-Name', ' Sample3_Uganda ')


def test_same_key_with_a_different_value_is_kept():
    from api.metagenome_similarity import is_already_shown
    sections = [[{'raw_k': 'sample_name', 'v': 'Sample3_Uganda'}]]
    assert not is_already_shown(sections, 'sample name', 'sample3_uganda')
    assert not is_already_shown(sections, 'sample alias', 'Sample3_Uganda')


def test_map_category_follows_sandpipers_host_or_ecological_call():
    from api.api import map_category
    assert map_category('host') == 'host_associated'
    assert map_category('ecological') == 'ecological'


def test_map_category_is_unclassified_without_a_sandpiper_call():
    from api.api import map_category
    assert map_category(None) == 'unclassified'
    assert map_category('something else') == 'unclassified'
