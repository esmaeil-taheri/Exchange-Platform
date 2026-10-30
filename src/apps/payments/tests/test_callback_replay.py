import pytest


@pytest.mark.django_db
@pytest.mark.parametrize('invoice_fixture', ['invoice', 'buy_invoice'])
@pytest.mark.parametrize('processed', [False, True])
def test_paid_callback_replay_does_not_verify_or_queue_again(
    request, api_client, bank_card, mock_gateway_verify_valid_hash,
    mock_task_deposit, mock_task_buy, mock_rate_limit, invoice_fixture, processed,
):
    invoice = request.getfixturevalue(invoice_fixture)
    url = '/api/v1/payments/zarinpal/callback'
    data = {'gateway_track_id': invoice.gateway_track_id}

    assert api_client.post(url, data).status_code == 200
    invoice.refresh_from_db()
    assert invoice.is_paid is True
    assert invoice.status == 'paid'
    invoice.is_processed = processed
    invoice.save(update_fields=['is_processed'])

    replay = api_client.post(url, data)

    assert replay.status_code == 200
    assert 'قبلاً' in replay.data['message']
    mock_gateway_verify_valid_hash.assert_called_once()
    if invoice_fixture == 'invoice':
        mock_task_deposit.assert_called_once()
        mock_task_buy.assert_not_called()
    else:
        mock_task_buy.assert_called_once()
        mock_task_deposit.assert_not_called()
