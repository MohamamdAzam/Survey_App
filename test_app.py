
import pytest
from survey_app import calculate_statistics, validate_payload, process_survey

def test_valid_payload():
    valid_data = {
        "user_id": "test_user123",
        "survey_results": [
            {"question_number": 1, "question_value": 7},
            {"question_number": 2, "question_value": 5},
            {"question_number": 3, "question_value": 3},
            {"question_number": 4, "question_value": 1},
            {"question_number": 5, "question_value": 6},
            {"question_number": 6, "question_value": 6},
            {"question_number": 7, "question_value": 2},
            {"question_number": 8, "question_value": 7},
            {"question_number": 9, "question_value": 6},
            {"question_number": 10, "question_value": 6}
        ]
    }
    is_valid, error_message = validate_payload(valid_data)
    assert is_valid
    assert error_message is None

def test_invalid_user_id():
    invalid_data = {
        "user_id": "test",
        "survey_results": [
            {"question_number": 1, "question_value": 7},
            {"question_number": 2, "question_value": 5},
            {"question_number": 3, "question_value": 3},
            {"question_number": 4, "question_value": 1},
            {"question_number": 5, "question_value": 6},
            {"question_number": 6, "question_value": 6},
            {"question_number": 7, "question_value": 2},
            {"question_number": 8, "question_value": 7},
            {"question_number": 9, "question_value": 6},
            {"question_number": 10, "question_value": 6}
        ]
    }
    is_valid, error_message = validate_payload(invalid_data)
    assert not is_valid
    assert error_message == "Invalid `user_id`. Must be a string with at least 5 characters."

def test_invalid_survey_results_length():
    invalid_data = {
        "user_id": "test_user123",
        "survey_results": [
            {"question_number": 1, "question_value": 7}
        ]
    }
    is_valid, error_message = validate_payload(invalid_data)
    assert not is_valid
    assert error_message == "`survey_results` must contain exactly 10 entries."

def test_invalid_question_number():
    invalid_data = {
        "user_id": "test_user123",
        "survey_results": [
            {"question_number": 11, "question_value": 7},
            {"question_number": 1, "question_value": 7},
            {"question_number": 2, "question_value": 5},
            {"question_number": 3, "question_value": 3},
            {"question_number": 4, "question_value": 1},
            {"question_number": 5, "question_value": 6},
            {"question_number": 6, "question_value": 6},
            {"question_number": 7, "question_value": 2},
            {"question_number": 8, "question_value": 7},
            {"question_number": 9, "question_value": 6}
        ]
    }
    is_valid, error_message = validate_payload(invalid_data)
    assert not is_valid
    assert error_message == "Each `question_number` must be an integer between 1 and 10."

def test_invalid_question_value():
    invalid_data = {
        "user_id": "test_user123",
        "survey_results": [
            {"question_number": 1, "question_value": 8},
            {"question_number": 2, "question_value": 5},
            {"question_number": 3, "question_value": 3},
            {"question_number": 4, "question_value": 1},
            {"question_number": 5, "question_value": 6},
            {"question_number": 6, "question_value": 6},
            {"question_number": 7, "question_value": 2},
            {"question_number": 8, "question_value": 7},
            {"question_number": 9, "question_value": 6},
            {"question_number": 10, "question_value": 6}
        ]
    }
    is_valid, error_message = validate_payload(invalid_data)
    assert not is_valid
    assert error_message == "Each `question_value` must be an integer between 1 and 7."

def test_duplicate_question_number():
    invalid_data = {
        "user_id": "test_user123",
        "survey_results": [
            {"question_number": 1, "question_value": 7},
            {"question_number": 1, "question_value": 5}, 
            {"question_number": 2, "question_value": 5},
            {"question_number": 3, "question_value": 3},
            {"question_number": 4, "question_value": 1},
            {"question_number": 5, "question_value": 6},
            {"question_number": 6, "question_value": 6},
            {"question_number": 7, "question_value": 2},
            {"question_number": 8, "question_value": 7},
            {"question_number": 9, "question_value": 6},
            {"question_number": 10, "question_value": 6}
        ]
    }
    is_valid, error_message = validate_payload(invalid_data)
    assert not is_valid
    assert error_message == "Duplicate `question_number` values are not allowed."


def test_process_survey_valid_input(mocker):
    valid_data = {
        "user_id": "test_user123",
        "survey_results": [
            {"question_number": 1, "question_value": 7},
            {"question_number": 2, "question_value": 7},
            {"question_number": 3, "question_value": 4},
            {"question_number": 4, "question_value": 1},
            {"question_number": 5, "question_value": 6},
            {"question_number": 6, "question_value": 6},
            {"question_number": 7, "question_value": 2},
            {"question_number": 8, "question_value": 7},
            {"question_number": 9, "question_value": 6},
            {"question_number": 10, "question_value": 6}
        ]
    }

    mocker.patch('survey_app.generate_description_from_gemini', return_value='Test description')
    mocker.patch('survey_app.collection.insert_one', return_value={'acknowledged': True, 'inserted_id': 'me'})
    result = process_survey(valid_data)

    assert result['status'] == 'success'
    assert result['description'] == 'Test description'
    assert result['survey_id'] == 'survey_id'


    survey_insert_mock = mocker.patch('survey_app.collection.insert_one')
    survey_insert_mock.assert_called_once_with({
        'user_id': valid_data['user_id'],
        'survey_results': valid_data['survey_results'],
        'description': 'Test description'
    })


def test_calculate_statistics():
    survey_results = [{"question_number": i, "question_value": i} for i in range(1, 11)]
    stats = calculate_statistics(survey_results)
    assert stats["mean"] == 5.5
    assert stats["median"] == 5.5
    assert round(stats["std_dev"], 2) == 3.03  

def test_validate_payload():
    valid_payload = {
        "user_id": "valid_user",
        "survey_results": [{"question_number": i, "question_value": 5} for i in range(1, 11)]
    }
    validate_payload(valid_payload)
    
    with pytest.raises(ValueError):
        validate_payload({"user_id": "short", "survey_results": []})

