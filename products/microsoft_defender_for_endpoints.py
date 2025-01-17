import csv
import json
import os
import time
import datetime
from pprint import pprint
import click

import urllib.request
import urllib.parse
import sys
import requests


def build_query(filters):
    query_base = ''

    for key, value in filters.items():
        if key == 'days':
            query_base += f'| where Timestamp > ago({value}d)'

        if key == 'minutes':
            query_base += f'| where Timestamp > ago({value}m)'

        if key == 'hostname':
            query_base += f'| where DeviceName contains "{value}"'

        if key == 'username':
            query_base += f'| where AccountName contains "{value}"'
    return query_base

def process_search(conn, base, user_query): 
    
    results = set()

    url = "https://api.securitycenter.microsoft.com/api/advancedqueries/run"
    query = "DeviceEvents" + base + user_query + "| project DeviceName, AccountName, ProcessCommandLine, FolderPath"

    query_obj = json.dumps({'Query': query}).encode("utf-8")    
    headers_obj = {
        "Authorization":"Bearer " + conn, 
        "Content-Type":"application/json", 
        "Accept": 'application/json'
        }
   
    try: 
        response = requests.post(url, data=query_obj, headers=headers_obj)
    except KeyboardInterrupt: 
        click.echo("Caught CTRL-C. Rerun surveyor")
    except Exception as e: 
        click.echo(f"There was an exception {e}")

    if response.status_code == 200: 
        for res in response.json()["Results"]: 
            results.add((res["DeviceName"], res["AccountName"], res["ProcessCommandLine"], res["FolderPath"]))

    else: 
        click.echo(f"We received the following status code {response.status_code}")
    
    return results

def nested_process_search(conn, criteria, base):
    results = set()
    
    url = "https://api.securitycenter.microsoft.com/api/advancedqueries/run"
    headers_obj = {
        "Authorization":"Bearer " + conn, 
        "Content-Type":"application/json", 
        "Accept": 'application/json'
        }

    query_base = build_query(base)
    try:
        for search_field, terms in criteria.items():            
            all_terms = ', '.join(f"'{term}'" for term in terms)
            if search_field == 'process_name':
                query = f"| where FileName has_any ({all_terms})"
            elif search_field == "filemod": 
                query = f"| where FileName has_any ({all_terms})"
            elif search_field == "ipaddr":
                query = f"| where RemoteIP has_any ({all_terms})"
            elif search_field == "cmdline": 
                query = f"| where ProcessCommandLine has_any ({all_terms})"
            elif search_field == "digsig_publisher": 
                query = f"| where Signer has_any ({all_terms})"
            elif search_field == "domain":
                query = f"| where RemoteUrl has_any ({all_terms})"
            elif search_field == "internal_name":
                query = f"| where ProcessVersionInfoInternalFileName has_any ({all_terms})"
            
            else: 
                continue
            
            query = "union DeviceEvents, DeviceFileCertificateInfo, DeviceProcessEvents" + query_base + query + "| project DeviceName, AccountName, ProcessCommandLine, FolderPath"


            data = json.dumps({'Query': query}).encode("utf-8")

            try: 
                response = requests.post(url, data=data, headers=headers_obj)
            except KeyboardInterrupt: 
                click.echo("Caught CTRL-C. Rerun surveyor")
            except Exception as e: 
                click.echo(f"There was an exception {e}")

            if response.status_code == 200: 
                for res in response.json()["Results"]: 
                    results.add((res["DeviceName"], res["AccountName"], res["ProcessCommandLine"], res["FolderPath"]))
            else: 
                click.echo(f"We received the following status code {response.status_code}")
    
    except Exception as e:
        click.echo(e)
        pass
    except KeyboardInterrupt:
        click.echo("Caught CTRL-C. Returning what we have . . .")

    
    return results