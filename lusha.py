"""Lusha API."""

import argparse

import pandas as pd

import requests


def append_cache(item, res, cache):
    """
    Add each retireved line to a CSV cache
    """
    print(res)
    item.set_value('emails', res[0])
    item.set_value('phones', res[1])
    cache.loc[len(cache)] = item
    cache.to_csv('cache.csv', sep=';', encoding='latin-1')

def find_row(item, cache):
    res = cache.loc[lambda df: df.firstname == item['firstname']]
    res = res.loc[lambda df: df.lastname == item['lastname']]
    res = res.loc[lambda df: df.company == item['company']]
    return res

def get_from_cache(item, cache):
    print('Item found in cache')
    res = find_row(item, cache)
    return res.loc[0]['emails'], res.loc[0]['phones']

def check_cache(item, cache):
    res = find_row(item, cache)
    return (len(res['phones']) or len(res['emails']))

def query_lusha(api_key, firstname, lastname, company=None, domain=None):
    """Query the lusha API.

    Documentation:
    https://www.lusha.co/docs#PersonAPI
    """
    base_url = 'https://api.lusha.co/person?firstName={firstname}&lastName={lastname}&'
    base_url = base_url.format(firstname=firstname, lastname=lastname)

    if company:
        company_request = base_url + 'company={company}'
        query = company_request.format(company=company)
    elif domain:
        domain_request = base_url + 'domain={domain}'
        query = domain_request.format(domain=domain)

    headers = {'api_key': api_key}
    return requests.get(query, headers=headers)


def parse_lusha_response(response):
    """Parse and return a dictionnary of objects.

    Documentation regarding responses from lusha:
    https://www.lusha.co/docs#PersonAPI
    """
    if response is None:
        return

    if response.status_code != 200:
        print('Error when querying ' + response.url)
        print('Error code ' + str(response.status_code))
        return

    if 'data' not in response.json():
        print('Querying ' + response.url)
        print('returned 0 results')
        return

    print('Querying ' + response.url)
    print('returned a result')

    data = response.json()['data']
    if isinstance(data, list):
        data = data[0]

    emails = [e['email'] for e in data['emailAddresses']]
    phones = [p['internationalNumber'] for p in data['phoneNumbers']]

    return emails, phones


def lushalize(api_key, firstname, lastname, company=None, domain=None):
    """Use lusha API to get information about someone."""
    if company is None and domain is None:
        print('ERROR: no company and no domain given for ' + firstname + ' ' + lastname)

    # Query by company first.
    if company is not None:
        response = query_lusha(api_key, firstname, lastname,
                               company=company)
        res = parse_lusha_response(response)

        # If there is a result with the company, do not bother querying using the
        # domain.
        if res is not None:
            return res

    # Query using the domain.
    if domain is not None:
        response = query_lusha(api_key, firstname, lastname,
                               domain=domain)
        res = parse_lusha_response(response)
        return res

    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='lusha API')
    parser.add_argument('--key', type=str, help='API KEY for lusha')
    parser.add_argument('--csv', type=str, help='Path to csv file')

    args = parser.parse_args()
    api_key = args.key
    csv_path = args.csv

    try:
        cache = pd.read_csv('cache.csv', encoding='latin-1', sep=';')
    except FileNotFoundError:
        cache = pd.DataFrame(columns=['firstname', 'lastname', 'company', 'domain', 'emails', 'phones'])

    df = pd.read_csv(csv_path, encoding='latin-1', sep=';')
    df = df.where(pd.notnull(df), None)
    df['emails'] = None
    df['phones'] = None
    for idx, row in df.iterrows():
        if check_cache(row, cache):
            res = get_from_cache(row, cache)
        else:
            res = lushalize(api_key, row['firstname'], row['lastname'], row['company'], row['domain'])
        if res is not None:
            if not check_cache(row, cache):
                append_cache(row, res, cache)
            df.set_value(idx, 'emails', res[0])
            df.set_value(idx, 'phones', res[1])
    df.to_csv('out.csv', index=False)
