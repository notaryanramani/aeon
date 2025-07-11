"""WEASEL classifier.

Dictionary based classifier based on SFA transform, BOSS and linear regression.
"""

__maintainer__ = []
__all__ = ["WEASEL"]

import math

import numpy as np
from joblib import Parallel, delayed
from numba import set_num_threads
from scipy.sparse import hstack
from sklearn.linear_model import LogisticRegression, RidgeClassifierCV
from sklearn.utils import check_random_state

from aeon.classification.base import BaseClassifier
from aeon.transformations.collection.dictionary_based import SFAFast
from aeon.utils.validation import check_n_jobs


class WEASEL(BaseClassifier):
    """
    Word Extraction for Time Series Classification (WEASEL).

    As described in [1]_. Overview: Input 'n' series length 'm'
    WEASEL is a dictionary classifier that builds a bag-of-patterns using SFA
    for different window lengths and learns a logistic regression classifier
    on this bag.

    There are these primary parameters:
            - alphabet_size: alphabet size
            - p-threshold: threshold used for chi^2-feature selection to
                        select best words.
            - anova: select best l/2 fourier coefficients other than first ones
            - bigrams: using bigrams of SFA words
            - binning_strategy: the binning strategy used to discretise into SFA words.
    WEASEL slides a window length *w* along the series. The *w* length window
    is shortened to an *l* length word through taking a Fourier transform and
    keeping the best *l/2* complex coefficients using an anova one-sided
    test. These *l* coefficients are then discretised into alpha possible
    symbols, to form a word of length *l*. A histogram of words for each
    series is formed and stored.
    For each window-length a bag is created and all words are joint into
    one bag-of-patterns. Words from different window-lengths are
    discriminated by different prefixes.
    *fit* involves training a logistic regression classifier on the single
    bag-of-patterns.

    predict uses the logistic regression classifier

    Parameters
    ----------
    anova : bool, default=True
        If True, the Fourier coefficient selection is done via a one-way
        ANOVA test. If False, the first Fourier coefficients are selected.
        Only applicable if labels are given.
    bigrams : bool, default=True
        Whether to create bigrams of SFA words.
    binning_strategy : str, default="information-gain"
        The binning method used to derive the breakpoints.
        one of {"equi-depth", "equi-width", "information-gain"}.
    window_inc : int, default=2
        WEASEL create a BoP model for each window sizes. This is the
        increment used to determine the next window size.
    p_threshold :  int, default=0.05 (disabled by default)
        Feature selection is applied based on the chi-squared test.
        This is the p-value threshold to use for chi-squared test on bag-of-words
        (lower means more strict). 1 indicates that the test
        should not be performed.
    alphabet_size : default = 4
        Number of possible letters (values) for each word.
    feature_selection : str, default: "chi2"
        Sets the feature selections strategy to be used. One of {"chi2", "none",
        "random"}.  Large amounts of memory may beneeded depending on the setting of
        bigrams (true is more) or alpha (larger is more).
        'chi2' reduces the number of words, keeping those above the 'p_threshold'.
        'random' reduces the number to at most 'max_feature_count',
        by randomly selecting features.
        'none' does not apply any feature selection and yields large bag of words.
    support_probabilities : bool, default: False
        If set to False, a RidgeClassifierCV will be trained, which has higher accuracy
        and is faster, yet does not support predict_proba.
        If set to True, a LogisticRegression will be trained, which does support
        predict_proba(), yet is slower and typically less accurate. predict_proba() is
        needed for example in Early-Classification like TEASER.
    class_weight{“balanced”, “balanced_subsample”}, dict or list of dicts, default=None
        From sklearn documentation:
        If not given, all classes are supposed to have weight one.
        The “balanced” mode uses the values of y to automatically adjust weights
        inversely proportional to class frequencies in the input data as
        n_samples / (n_classes * np.bincount(y))
        The “balanced_subsample” mode is the same as “balanced” except that weights
        are computed based on the bootstrap sample for every tree grown.
        For multi-output, the weights of each column of y will be multiplied.
        Note that these weights will be multiplied with sample_weight (passed through
        the fit method) if sample_weight is specified.
    random_state : int, RandomState instance or None, default=None
        If `int`, random_state is the seed used by the random number generator;
        If `RandomState` instance, random_state is the random number generator;
        If `None`, the random number generator is the `RandomState` instance used
        by `np.random`.

    See Also
    --------
    MUSE
        Multivariate version of WEASEL.

    Notes
    -----
    For the Java version, see
    - `Original Publication <https://github.com/patrickzib/SFA>`_.
    - `TSML <https://github.com/uea-machine-learning/tsml/blob/master/src/main/java
    /tsml/classifiers/dictionary_based/WEASEL.java>`_.

    References
    ----------
    .. [1] Patrick Schäfer and Ulf Leser, "Fast and Accurate Time Series Classification
    with WEASEL", in proc ACM on Conference on Information and Knowledge Management,
    2017, https://dl.acm.org/doi/10.1145/3132847.3132980

    Examples
    --------
    >>> from aeon.classification.dictionary_based import WEASEL
    >>> from aeon.datasets import load_unit_test
    >>> X_train, y_train = load_unit_test(split="train")
    >>> X_test, y_test = load_unit_test(split="test")
    >>> clf = WEASEL(window_inc=4)
    >>> clf.fit(X_train, y_train)
    WEASEL(...)
    >>> y_pred = clf.predict(X_test)
    """

    _tags = {
        "capability:multithreading": True,
        "algorithm_type": "dictionary",
    }

    def __init__(
        self,
        anova=True,
        bigrams=True,
        binning_strategy="information-gain",
        window_inc=2,
        p_threshold=0.05,
        alphabet_size=4,
        feature_selection="chi2",
        support_probabilities=False,
        class_weight=None,
        n_jobs=1,
        random_state=None,
    ):
        self.alphabet_size = alphabet_size
        # feature selection is applied based on the chi-squared test.
        self.p_threshold = p_threshold
        self.anova = anova
        self.norm_options = [False]
        self.word_lengths = [4, 6]
        self.bigrams = bigrams
        self.binning_strategy = binning_strategy
        self.min_window = 6
        self.max_window = 100
        self.feature_selection = feature_selection
        self.window_inc = window_inc
        self.highest_bit = -1
        self.window_sizes = []
        self.n_timepoints = 0
        self.n_cases = 0
        self.SFA_transformers = []
        self.clf = None
        self.support_probabilities = support_probabilities

        self.random_state = random_state
        self.n_jobs = n_jobs
        self.class_weight = class_weight

        set_num_threads(n_jobs)

        super().__init__()

    def _fit(self, X, y):
        """Build a WEASEL classifiers from the training set (X, y).

        Parameters
        ----------
        X : 3D np.ndarray
            The training data shape = (n_cases, n_channels, n_timepoints).
        y : 1D np.ndarray
            The class labels shape = (n_cases).

        Returns
        -------
        self :
            Reference to self.
        """
        # Window length parameter space dependent on series length
        self.n_cases, self.n_timepoints = X.shape[0], X.shape[-1]
        self._n_jobs = check_n_jobs(self.n_jobs)

        win_inc = self._compute_window_inc()
        self.max_window = int(min(self.n_timepoints, self.max_window))
        if self.min_window > self.max_window:
            raise ValueError(
                f"Error in WEASEL, min_window ="
                f"{self.min_window} is bigger"
                f" than max_window ={self.max_window},"
                f" series length is {self.n_timepoints}"
                f" try set min_window to be smaller than series length in "
                f"the constructor, but the classifier may not work at "
                f"all with very short series"
            )
        self.window_sizes = list(range(self.min_window, self.max_window, win_inc))
        self.highest_bit = (math.ceil(math.log2(self.max_window))) + 1

        parallel_res = Parallel(n_jobs=self.n_jobs, prefer="threads")(
            delayed(_parallel_fit)(
                X,
                y,
                window_size,
                self.word_lengths,
                self.alphabet_size,
                self.norm_options,
                self.anova,
                self.binning_strategy,
                self.feature_selection,
                self.bigrams,
                self.n_jobs,
            )
            for window_size in self.window_sizes
        )

        all_words = []
        for sfa_words, transformer in parallel_res:
            self.SFA_transformers.append(transformer)
            all_words.append(sfa_words)
        if type(all_words[0]) is np.ndarray:
            all_words = np.concatenate(all_words, axis=1)
        else:
            all_words = hstack(all_words)

        # Ridge Classifier does not give probabilities
        if not self.support_probabilities:
            self.clf = RidgeClassifierCV(
                alphas=np.logspace(-3, 3, 10), class_weight=self.class_weight
            )
        else:
            self.clf = LogisticRegression(
                max_iter=5000,
                solver="liblinear",
                dual=True,
                class_weight=self.class_weight,
                penalty="l2",
                random_state=self.random_state,
                n_jobs=self.n_jobs,
            )

        self.clf.fit(all_words, y)

        self.total_features_count = all_words.shape[1]
        if hasattr(self.clf, "best_score_"):
            self.cross_val_score = self.clf.best_score_

        return self

    def _predict(self, X) -> np.ndarray:
        """Predict class values of n instances in X.

        Parameters
        ----------
        X : 3D np.ndarray
            The data to make predictions for, shape = (n_cases, n_channels,
            n_timepoints).

        Returns
        -------
        1D np.ndarray
            Predicted class labels shape = (n_cases).
        """
        bag = self._transform_words(X)
        return self.clf.predict(bag)

    def _predict_proba(self, X) -> np.ndarray:
        """Predict class probabilities for n instances in X.

        Parameters
        ----------
        X : 3D np.ndarray
            The data to make predictions for, shape = (n_cases, n_channels,
            n_timepoints).

        Returns
        -------
        2D np.ndarray
            Predicted class labels shape = (n_cases).
        """
        bag = self._transform_words(X)
        if self.support_probabilities:
            return self.clf.predict_proba(bag)
        else:
            raise ValueError(
                "Error in WEASEL, please set support_probabilities=True, to"
                + "allow for probabilities to be computed."
            )

    def _transform_words(self, X):
        parallel_res = Parallel(n_jobs=self._n_jobs, prefer="threads")(
            delayed(transformer.transform)(X) for transformer in self.SFA_transformers
        )
        all_words = list(parallel_res)
        return (
            np.concatenate(all_words, axis=1)
            if type(all_words[0]) is np.ndarray
            else hstack(all_words)
        )

    def _compute_window_inc(self):
        return 1 if self.n_timepoints < 100 else self.window_inc

    @classmethod
    def _get_test_params(cls, parameter_set="default"):
        """Return testing parameter settings for the estimator.

        Parameters
        ----------
        parameter_set : str, default="default"
            Name of the set of test parameters to return, for use in tests. If no
            special parameters are defined for a value, will return `"default"` set.

        Returns
        -------
        dict or list of dict
            Parameters to create testing instances of the class.
            Each dict are parameters to construct an "interesting" test instance, i.e.,
            `MyClass(**params)` or `MyClass(**params[i])` creates a valid test instance.
        """
        return {
            "window_inc": 4,
            "support_probabilities": True,
            "bigrams": False,
            "feature_selection": "none",
            "alphabet_size": 2,
        }


def _parallel_fit(
    X,
    y,
    window_size,
    word_lengths,
    alphabet_size,
    norm_options,
    anova,
    binning_strategy,
    feature_selection,
    bigrams,
    n_jobs,
):
    rng = check_random_state(window_size)
    transformer = SFAFast(
        word_length=rng.choice(word_lengths),
        alphabet_size=alphabet_size,
        window_size=window_size,
        norm=rng.choice(norm_options),
        anova=anova,
        binning_method=binning_strategy,
        bigrams=bigrams,
        feature_selection=feature_selection,
        remove_repeat_words=False,
        save_words=False,
        n_jobs=n_jobs,
    )

    all_words = transformer.fit_transform(X, y)
    return all_words, transformer
