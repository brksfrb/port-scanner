# Function to convert an IP address to a tuple of integers for numerical comparison
def ip_to_tuple(ip):
    return tuple(map(int, ip.split('.')))


# Function to sort the IPs by subnet and IP numerically
def sort_ips(scanned_ips):
    # Sort the IP addresses within each subnet numerically
    for subnet, ips in scanned_ips.items():
        scanned_ips[subnet] = sorted(ips, key=ip_to_tuple)

    # Sort the subnets numerically
    return dict(sorted(scanned_ips.items()))