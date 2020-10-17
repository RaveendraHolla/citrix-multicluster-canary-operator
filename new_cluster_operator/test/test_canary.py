import unittest
from unittest import mock
import yaml
import sys
import copy

sys.path.insert(0, '../src')
import canary

class CanaryTestCase(unittest.TestCase):
    @mock.patch('canary.read_existing_gtp')
    @mock.patch('canary.apply_gtp')
    @mock.patch('canary.calculate_health_score')
    def test_handle_canary_crd(self, mock_calculate_health_score, mock_apply_gtp, mock_read_gtp):
        with open("gtp_cr.yaml") as f:
            gtp_dict = yaml.load(f, Loader=yaml.FullLoader)
        mock_read_gtp.return_value = gtp_dict
        gtp_dict_original = copy.deepcopy(gtp_dict)
        with open("canary_cr.yaml") as f:
            canary_dict = yaml.load(f, Loader=yaml.FullLoader)
        mock_calculate_health_score.return_value = 95
        assert(canary.handle_canary_crd(canary_dict) is True)
        mock_calculate_health_score.return_value = 85
        mock_read_gtp.return_value = gtp_dict_original
        assert(canary.handle_canary_crd(canary_dict) is False)

if __name__ == '__main__':
    unittest.main()
