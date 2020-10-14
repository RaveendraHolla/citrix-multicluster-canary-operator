import unittest
from unittest import mock
import yaml

import canary

class CanaryTestCase(unittest.TestCase):
    @mock.patch('canary.read_existing_gtp')
    @mock.patch('canary.apply_gtp')
    def test_handle_multicluster_canary_crd(self, mock_apply_gtp, mock_read_gtp):
        with open("gtp_cr.yaml") as f:
            gtp_dict = yaml.load(f, Loader=yaml.FullLoader)
        mock_read_gtp.return_value = gtp_dict
        with open("canary_cr.yaml") as f:
            canary_dict = yaml.load(f, Loader=yaml.FullLoader)
        assert(canary.handle_multicluster_canary_crd(canary_dict) is True)

if __name__ == '__main__':
    unittest.main()
