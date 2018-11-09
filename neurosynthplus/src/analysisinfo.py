from collections import OrderedDict
from string import punctuation
import pandas as pd


class BiOrderedDict(OrderedDict):
    """
    Bidirectional ordered dictionary for a small storage
    """
    def get_key(self, value):
        for k, v in self.items():
            if v == value:
                return v

    def get_keys(self, value):
        return [v for k, v in self.items() if v == value]

    def reverse(self, include=None):
        """
        :param include: a function that determines if a key is included
        :return: reversed dictionary {value: key}
        """
        if include:
            return BiOrderedDict([(v, k) for k, v in self.items() if include(k)])
        return BiOrderedDict([(v, k) for k, v in self.items()])


class AnalysisInfo(OrderedDict):
    """
    Handle information strings (e.g. NeuroSynth expressions and image names).
    """
    img_names = BiOrderedDict(
        [('association-test_z', 'Reverse inference z score'),
         ('pFgA_given_pF=', 'Reverse inference probability with an objective prior'),
         ('association-test_z_FDR_', 'Association test (reverse inference z score) '
                                     'with multiple comparison correction'),
         ('pFgA', 'Reverse inference probability'),

         ('uniformity-test_z', 'Forward inference z score'),
         ('pAgF_given_pF=', 'Forward inference activation probability with a uniform prior'),
         ('uniformity-test_z_FDR_', 'Uniformity test (forward inference z score) '
                                    'with multiple comparison correction'),
         ('pAgF', 'Forward inference probability'),

         ('pA', 'Base rate probability of activation')])

    regular_img_names = ['pA', 'pAgF', 'pFgA', 'uniformity-test_z', 'association-test_z']
    pre_prior = 'given_pF='
    pre_fdr = '_z_FDR_'

    def __init__(self, *args, **kwargs):
        super(AnalysisInfo, self).__init__(*args, **kwargs)

    @staticmethod
    def shorten_expr(expr):
        abbr = expr.split(' ', maxsplit=1)[0]
        return abbr.strip(punctuation)

    @classmethod
    def get_num_from_img_name(cls, img_name):
        if img_name in AnalysisInfo.regular_img_names:
            return {}
        if cls.pre_prior in img_name:
            num_index = img_name.index(cls.pre_prior) + len(cls.pre_prior)
            num = img_name[num_index:]
            return {'prior': float(num)}
        if cls.pre_fdr in img_name:
            num_index = img_name.index(cls.pre_fdr) + len(cls.pre_fdr)
            num = img_name[num_index:]
            return {'fdr': float(num)}
        return {}

    @classmethod
    def add_num_to_img_name(cls, img_name, prior=None, fdr=None):
        if (cls.pre_prior in img_name) and prior:
            return img_name + '%0.2f' % prior
        if (cls.pre_fdr in img_name) and fdr:
            return img_name + str(fdr)
        return img_name

    @classmethod
    def order_images(cls, images):
        """
        :param images: (iterable) names of images
        :return: a list of given images, ordered
        """
        result = []
        for img in images:
            for part in cls.img_names.keys():
                if part in img:
                    result.append(img)
                    continue
        return result

    def as_pandas_df(self):
        """
        Return the information as a pandas data frame
        """
        return pd.DataFrame(list(self.values()), index=list(self.keys()))
