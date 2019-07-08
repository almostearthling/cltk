import regex as re

from cltk.prosody.latin.Syllabifier import Syllabifier
from prose_rhythm.normalizer import Normalizer

class Scansion:
    """
    Prepossesses Latin text for prose rhythm analysis.
    """

    SHORT_VOWELS = ["a", "e", "i", "o", "u", "y"]
    LONG_VOWELS = ["ā", "ē", "ī", "ō", "ū"]
    VOWELS = SHORT_VOWELS + LONG_VOWELS
    DIPHTHONGS = ["ae", "au", "ei", "oe", "ui"]

    SINGLE_CONSONANTS = ["b", "c", "d", "g", "k", "l", "m", "n", "p", "q", "r",
                         "s", "t", "v", "f", "j"]
    DOUBLE_CONSONANTS = ["x", "z"]
    CONSONANTS = SINGLE_CONSONANTS + DOUBLE_CONSONANTS
    DIGRAPHS = ["ch", "ph", "th", "qu"]
    LIQUIDS = ["r", "l"]
    MUTES = ["b", "p", "d", "t", "c", "g"]
    MUTE_LIQUID_EXCEPTIONS = ["gl", "bl"]
    NASALS = ["m", "n"]
    SESTS = ["sc", "sm", "sp", "st", "z"]

    def __init__(self, punctuation=None):
        self.punctuation = [".", "?", "!", ";", ":"] if punctuation is None else punctuation
        self.syllabifier = Syllabifier()
        self.normalizer = Normalizer()


    def _tokenize_syllables(self, word):
        """
        Tokenize syllables for word.
        "mihi" -> [{"syllable": "mi", index: 0, ... } ... ]
        Syllable properties:
            syllable: string -> syllable
            index: int -> postion in word
            long_by_nature: bool -> is syllable long by nature
            accented: bool -> does receive accent
            long_by_position: bool -> is syllable long by position
        :param word: string
        :return: list
        """
        syllable_tokens = []
        syllables = self.syllabifier.syllabify(word)

        longs = self.LONG_VOWELS + self.DIPHTHONGS

        for i, _ in enumerate(syllables):
            # basic properties
            syllable_dict = {"syllable": syllables[i], "index": i, "elide": (False, None)}

            # is long by nature
            if any(long in syllables[i] for long in longs):
                if syllables[i][:3] != "qui":
                    syllable_dict["long_by_nature"] = True
                else:
                    syllable_dict["long_by_nature"] = False
            else:
                syllable_dict["long_by_nature"] = False

            # long by position intra word
            if i < len(syllables) - 1 and \
                    syllable_dict["syllable"][-1] in self.CONSONANTS:
                if syllable_dict["syllable"][-1] in self.MUTES and syllables[i + 1][0] in self.LIQUIDS and syllable_dict["syllable"][-1]+syllables[i + 1][0] not in self.MUTE_LIQUID_EXCEPTIONS:
                    syllable_dict["long_by_position"] = \
                        (False, "mute+liquid")
                elif syllable_dict["syllable"][-1] in self.DOUBLE_CONSONANTS or \
                        syllables[i + 1][0] in self.CONSONANTS:
                    syllable_dict["long_by_position"] = (True, None)
                else:
                    syllable_dict["long_by_position"] = (False, None)
            elif i < len(syllables) - 1 and syllable_dict["syllable"][-1] in \
                    self.VOWELS and len(syllables[i + 1]) > 1:
                if syllables[i + 1][0] in self.MUTES and syllables[i + 1][1] in self.LIQUIDS and syllables[i + 1][0]+syllables[i + 1][1] not in self.MUTE_LIQUID_EXCEPTIONS:
                    syllable_dict["long_by_position"] = \
                        (False, "mute+liquid")
                elif syllables[i + 1][0] in self.CONSONANTS and syllables[i + 1][1] in \
                        self.CONSONANTS or syllables[i + 1][0] in self.DOUBLE_CONSONANTS:
                    syllable_dict["long_by_position"] = (True, None)
                else:
                    syllable_dict["long_by_position"] = (False, None)
            elif len(syllable_dict["syllable"]) > 2 and  syllable_dict["syllable"][-1] in self.CONSONANTS and \
                syllable_dict["syllable"][-2] in self.CONSONANTS and syllable_dict["syllable"][-3] in self.VOWELS:
                syllable_dict["long_by_position"] = (True, None)
            else:
                syllable_dict["long_by_position"] = (False, None)

            syllable_tokens.append(syllable_dict)

            # is accented
            if len(syllables) > 2 and i == len(syllables) - 2:
                if syllable_dict["long_by_nature"] or syllable_dict["long_by_position"][0]:
                    syllable_dict["accented"] = True
                else:
                    syllable_tokens[i - 1]["accented"] = True
            elif len(syllables) == 2 and i == 0 or len(syllables) == 1:
                syllable_dict["accented"] = True

            syllable_dict["accented"] = False if "accented" not in syllable_dict else True

        return syllable_tokens

    def _tokenize_words(self, sentence):
        """
        Tokenize words for sentence.
        "Puella bona est" -> [{word: puella, index: 0, ... }, ... ]
        Word properties:
            word: string -> word
            index: int -> position in sentence
            syllables: list -> list of syllable objects
            syllables_count: int -> number of syllables in word
        :param sentence: string
        :return: list
        """
        tokens = []
        split_sent = [word for word in sentence.split(" ") if word != '']
        for i, word in enumerate(split_sent):
            if len(word) == 1 and word not in self.VOWELS:
                break
            # basic properties
            word_dict = {"word": split_sent[i], "index": i}

            # syllables and syllables count
            word_dict["syllables"] = self._tokenize_syllables(split_sent[i])
            word_dict["syllables_count"] = len(word_dict["syllables"])
            try:
                if i != 0 and word_dict["syllables"][0]["syllable"][0] in \
                        self.VOWELS or i != 0 and \
                        word_dict["syllables"][0]["syllable"][0] == "h":
                    last_syll_prev_word = tokens[i - 1]["syllables"][-1]
                    if last_syll_prev_word["syllable"][-1] in \
                            self.LONG_VOWELS or \
                            last_syll_prev_word["syllable"][-1] == "m":
                        last_syll_prev_word["elide"] = (True, "strong")
                    elif len(last_syll_prev_word["syllable"]) > 1 and \
                            last_syll_prev_word["syllable"][-2:] in self.DIPHTHONGS:
                        last_syll_prev_word["elide"] = (True, "strong")
                    elif last_syll_prev_word["syllable"][-1] in self.SHORT_VOWELS:
                        last_syll_prev_word["elide"] = (True, "weak")
                # long by position inter word
                if i > 0 and tokens[i - 1]["syllables"][-1]["syllable"][-1] in \
                        self.CONSONANTS and \
                        word_dict["syllables"][0]["syllable"][0] in self.CONSONANTS:
                    # previous word ends in consonant and current word begins with consonant
                    tokens[i - 1]["syllables"][-1]["long_by_position"] = (True, None)
                elif i > 0 and tokens[i - 1]["syllables"][-1]["syllable"][-1] in \
                        self.VOWELS and \
                        word_dict["syllables"][0]["syllable"][0] in self.CONSONANTS:
                    # previous word ends in vowel and current word begins in consonant
                    if any(sest in word_dict["syllables"][0]["syllable"] for
                           sest in self.SESTS):
                        # current word begins with sest
                        tokens[i - 1]["syllables"][-1]["long_by_position"] = (False, "sest")
                    elif word_dict["syllables"][0]["syllable"][0] in self.MUTES and \
                            word_dict["syllables"][0]["syllable"][1] in self.LIQUIDS:
                        # current word begins with mute + liquid
                        tokens[i - 1]["syllables"][-1]["long_by_position"] = (False, "mute+liquid")
                    elif word_dict["syllables"][0]["syllable"][0] in \
                            self.DOUBLE_CONSONANTS or\
                            word_dict["syllables"][0]["syllable"][1] in self.CONSONANTS:
                        # current word begins 2 consonants
                        tokens[i - 1]["syllables"][-1]["long_by_position"] = (True, None)
            except IndexError:
                print(f'An error occurred when attempting to tokenize \'{word}\'.')
                raise

            tokens.append(word_dict)

        return tokens

    def tokenize(self, text):
        """
        Tokenize text on supplied characters.
        "Puella bona est. Puer malus est." ->
        [ [{word: puella, syllables: [...], index: 0}, ... ], ... ]
        :return:list
        """

        tokenized_sentences = text.split('.')

        tokenized_text = []
        for sentence in tokenized_sentences:
            sentence_dict = {}
            sentence_dict["plain_text_sentence"] = sentence
            sentence_dict["structured_sentence"] = self._tokenize_words(sentence)
            tokenized_text.append(sentence_dict)

        return tokenized_text

    def process_syllables(self, flat_syllable_list):
        """
        Return flat list of syllables with final syllable
        removed and list reversed. Elided syllables
        are removed as well
        """
        remove_elided = [syll for syll in flat_syllable_list if not syll['elide'][0]]
        processed_sylls = remove_elided[:-1]
        return processed_sylls[::-1]

    def get_rhythms(self, tokens, include_sentence=True):
        """
        Return a flat list of rhythms.
        Desired clausula length is passed as a parameter. Clausula shorter than the specified
        length can be exluded.
        :return:
        """
        clausulae = []
        abbrev_excluded = 0
        bracket_excluded = 0
        short_clausulae = 0
        other_excluded = 0
        for sentence in tokens['text']:
            sentence_clausula = []
            syllable_count = sum([word['syllables_count'] for word in sentence['structured_sentence']])
            if not sentence['contains_abbrev'] and not sentence['contains_bracket_text'] and syllable_count > 3:
                syllables = [word['syllables'] for word in sentence['structured_sentence']]
                flat_syllables = [syllable for word in syllables for syllable in word]
                flat_syllables = self.process_syllables(flat_syllables)
                for syllable in flat_syllables:
                    if len(sentence_clausula) < self.clausula_length - 1:
                        if syllable['long_by_nature'] or syllable['long_by_position'][0]:
                            sentence_clausula.append('-')
                        else:
                            sentence_clausula.append('u')
            else:
                if sentence['contains_abbrev']:
                    abbrev_excluded += 1
                elif sentence['contains_bracket_text']:
                    bracket_excluded += 1
                elif syllable_count > 0 and syllable_count < 4:
                    short_clausulae += 1
                else:
                    other_excluded += 1
            sentence_clausula = sentence_clausula[::-1]
            sentence_clausula.append('x')
            if include_sentence:
                clausulae.append((sentence['plain_text_sentence'], ''.join(sentence_clausula)))
            else:
                clausulae.append(''.join(sentence_clausula))
        clausulae = clausulae[:-1]
        clausulae.append(sum([abbrev_excluded, bracket_excluded, short_clausulae, other_excluded])-1)
        clausulae.append(abbrev_excluded)
        clausulae.append(bracket_excluded)
        clausulae.append(short_clausulae)
        clausulae.append(other_excluded)
        return clausulae