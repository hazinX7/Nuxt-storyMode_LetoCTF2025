from CTFd.plugins.flags import CTFdRegexFlag


def test_valid_regex_match_case_sensitive():
    flag = CTFdRegexFlag()
    flag.content = r"^[A-Z]\d{3}$"
    flag.data = "case_sensitive"
    provided_flag = "A123"
    assert flag.compare(flag, provided_flag)


def test_valid_regex_match_case_insensitive():
    flag = CTFdRegexFlag()
    flag.content = r"^[a-z]\d{3}$"
    flag.data = "case_insensitive"
    provided_flag = "A123"
    assert flag.compare(flag, provided_flag)


def test_invalid_regex_match():
    flag = CTFdRegexFlag()
    flag.content = r"^[A-Z]\d{3}$"
    flag.data = "case_sensitive"
    provided_flag = "invalid"
    assert not flag.compare(flag, provided_flag)
