import boto3

ssm = boto3.client('ssm')

p = {
    'name' : 123,
    'value' : 55
}

print(p['name'])

parameter = ssm.get_parameter(Name = '/myweb/database1_password',WithDecryption = True)  # aws parameter store 에서 만든 이름

print(type(parameter))
print(parameter['Parameter']['Value'])
print(type(parameter['Parameter']['Value']
      ))