import math
import ipaddress
import requests


def exclude_from_subnet(base_subnet, exclude_subnets):
    """
    从基础子网中排除指定的子网列表，返回剩余的子网列表。

    :param base_subnet: 基础子网，格式为CIDR表示法（如 "192.168.1.0/24"）
    :param exclude_subnets: 需要排除的子网列表，每个子网为CIDR表示法
    :return: 排除指定子网后的剩余子网列表
    """
    # 将基础子网转换为IPv4Network对象
    base_network = ipaddress.ip_network(base_subnet)

    # 将排除的子网列表转换为IPv4Network对象
    exclude_networks = [ipaddress.ip_network(subnet) for subnet in exclude_subnets]

    # 初始化结果列表，包含基础子网
    result = [base_network]

    # 遍历每个排除的子网
    for exclude_network in exclude_networks:
        new_result = []
        for network in result:
            # 如果当前网络与排除的网络有重叠，则进行排除操作
            if network.overlaps(exclude_network):
                # 使用address_exclude方法将网络分割成不重叠的子网
                for subnet in network.address_exclude(exclude_network):
                    new_result.append(subnet)
            else:
                # 如果没有重叠，则保留当前网络
                new_result.append(network)
        result = new_result

    return result


# 下载APNIC的IP信息
content = None
try:
    url = "http://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest"
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise requests.exceptions.RequestException("Status code is not 200")
    content = response.text.split('\n')
except Exception as e:
    print(f'Error when requesting APNIC data.\n{e}')

# 初始化中国的IPv4地址段列表
china_ipv4 = []

if content:
    # 提取中国的IPv4地址段并计算CIDR
    for line in content:
        if "apnic|CN|ipv4|" in line:
            parts = line.strip().split('|')
            ip = parts[3]  # IP地址
            num_ip = int(parts[4])  # IP地址数量
            cidr = 32 - int(math.log2(num_ip))  # 计算CIDR前缀长度
            china_ipv4.append(f"{ip}/{cidr}")  # 将IP地址和CIDR前缀长度组合成CIDR表示法

# 将中国的IPv4地址段转换为IPv4Network对象，并合并重叠的子网
china_ipv4_networks = [ipaddress.IPv4Network(net) for net in china_ipv4]
china_ipv4_networks = list(ipaddress.collapse_addresses(china_ipv4_networks))

# 定义需要排除的网络（公共网络、多播网络和私有网络）
v4_constants = ipaddress._IPv4Constants
reversed_networks = [v4_constants._public_network, v4_constants._multicast_network] + v4_constants._private_networks

# 从全局IPv4地址空间中排除中国的IPv4地址段和其他需要排除的网络
not_china_ipv4_networks = exclude_from_subnet("0.0.0.0/0", reversed_networks + china_ipv4_networks)
not_china_ipv4_networks = list(ipaddress.collapse_addresses(not_china_ipv4_networks))

# 将中国的IPv4地址段写入文件
with open("china_ip.txt", 'w') as f:
    for each in china_ipv4_networks:
        f.write(str(each) + '\n')

# 将非中国的IPv4地址段写入文件
with open("not_china_ip.txt", 'w') as f:
    for each in not_china_ipv4_networks:
        f.write(str(each) + '\n')
