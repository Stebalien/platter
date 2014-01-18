import dbus
import dbus.service

BUS_NAME = 'com.stebalien.platter'
SERVER_OBJECT = '/com/stebalien/platter'
SERVER_INTERFACE = BUS_NAME+'.Server'

class PlatterServerDBus(dbus.service.Object):
    def __init__(self, server, bus=None):
        self.server = server
        if not bus:
            bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(BUS_NAME, bus=bus)
        dbus.service.Object.__init__(self, bus_name, SERVER_OBJECT)

    @dbus.service.method(dbus_interface=SERVER_INTERFACE, in_signature='as')
    def AddFiles(self, files):
        self.server.serve(files)

def get_instance(bus=None):
    if not bus:
        bus = dbus.SessionBus()
    try:
        return dbus.Interface(bus.get_object(BUS_NAME, SERVER_OBJECT), dbus_interface=SERVER_INTERFACE)
    except dbus.DBusException:
        return None
