# use this to get the ns for opcua
from opcua import Client

url = "opc.tcp://127.0.0.1:4840/freeopcua/server/"
c = Client(url); c.connect()

root = c.get_objects_node()
machine = None
for child in root.get_children():
    dn = child.get_display_name().Text
    if dn == "InjectionMouldingMachine":
        machine = child
        break

print("Found InjectionMouldingMachine at", machine.nodeid)
print("Children:")
for child in machine.get_children():
    name = child.get_display_name().Text
    nid  = child.nodeid.to_string()
    print(f"  {name:20s} - {nid}")
c.disconnect()
