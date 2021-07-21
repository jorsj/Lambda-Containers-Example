import boto3
import awswrangler as wr
import urllib.parse


def handler(event, context):

    session = boto3.session.Session(profile_name='sandbox')

    for record in event['Records']:

        eventName = record['eventName']
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(
            record['s3']['object']['key'], encoding='utf-8')
        uri = f's3://{bucket}/{key}'

        if eventName == 'ObjectCreated:Put':
            try:
                ans = proc_anclaje(uri)
                carga = proc_write(ans, session)
                print(f'[{uri}]: Done!', carga)
            except Exception as e:
                print(f'[{uri}]: Error', e)
        else:
            print(f'[{uri}]: Skipped', eventName)

    return 'End of function reached'


def proc_anclaje(uri, session):

    tp = wr.s3.read_excel(uri, session)
    location = tp.iloc[:, 0:2].drop_duplicates().values  # x, y

    if location.shape[0] != 1:
        return(False, "Not unique value. It seems the file has multiple moorings.")

    tp.columns = ['longitude', 'latitude', 'datetime', 'depth_m',
                  'temperature_C', 'presure_m']  # TODO: do it auto

    data = tp.melt(['longitude', 'latitude', 'datetime'])

    return True, data


def proc_write(lista, session):
    if lista[0]:
        print('Writing')
        data = lista[1]
        for measurement in data.variable.unique():
            temp = data[data.variable == measurement].dropna()
            temp.rename(columns={'value': measurement}, inplace=True)
            rejected_records = wr.timestream.write(
                df=temp,
                database="uach-test",
                table="test",
                time_col="datetime",
                measure_col=measurement,
                dimensions_cols=["longitude", "latitude"],
                num_threads=10,
                boto3_session=session
            )
        return True, len(rejected_records) == 0

    else:
        print('Something is wrong..')
        return False, None
