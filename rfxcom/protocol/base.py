"""
Base Protocol
=============

The base package used to define the domain models for Packets and and Packet
Handlers.

"""

from datetime import datetime
from logging import getLogger

from rfxcom.exceptions import (InvalidPacketLength, MalformedPacket,
                               UnknownPacketType, UnknownPacketSubtype,
                               RFXComException)


class BasePacket:
    """The BasePacket class defines a packet that can be sent or received by
    the rfxtrx. It provides a number of simple helper methods and outlines the
    base API.
    """

    def __init__(self):
        """The BasePacket class is initialised with no arguments. It simply
        sets up a number of instance attributes when its created.
        """

        self.log = getLogger('rfxcom.protocol.%s' % self.__class__.__name__)
        self.PACKET_TYPES = {}
        self.PACKET_SUBTYPES = {}

    def dump_hex(self, data):
        """Given some bytes return the hex representation.

        :param data: bytearray to be formatted as a string
        :type data: bytearray

        :return: The formatted bytes as a readable hex string.
        :rtype: string
        """
        return "0x%s" % (''.join('{:02x}'.format(x) for x in data)).upper()

    def parse(self, data):
        """Stub method to be implemented by subclasses. The parse method
        should accept a bytearray, parse it and return a dictionary containing
        the parsed values.

        :param data: bytearray to be parsed
        :type data: bytearray

        :raises: :py:class:`NotImplementedError`: if this method isn't
            implemented by the subclass

        """
        raise NotImplementedError()

    def parse_header_part(self, data):
        """Extracts and converts the RFX common header part of all valid
        packets to a plain dictionary. RFX header part is the 4 bytes prior
        the sensor vendor specific data part.

        The RFX common header part contains respectively:
        - packet length
        - packet type
        - packet sub-type
        - sequence number

        :param data: bytearray of received data
        :type data: bytearray

        """
        packet_length = data[0]
        packet_type = data[1]
        packet_subtype = data[2]
        sequence_number = data[3]
        return {
            'packet_length': packet_length,
            'packet_type': packet_type,
            'packet_type_name': self.PACKET_TYPES.get(packet_type),
            'packet_subtype': packet_subtype,
            'packet_subtype_name': self.PACKET_SUBTYPES.get(packet_subtype),
            'sequence_number': sequence_number
        }

    def load(self, data):
        """This is the entrance method for all data which is used to store the
        raw data and start parsing the data.

        :param data: The raw untouched bytearray as recieved by the RFXtrx
        :type data: bytearray

        :return: The parsed data represented in a dictionary
        :rtype: dict
        """
        self.loaded_at = datetime.utcnow()
        self.raw = data
        self.data = self.parse(data)
        return self.data


class BasePacketHandler(BasePacket):

    def can_handle(self, data):
        """Determine if the packet handler understand and can parse this
        packet. This is defined by the checks in the ``validate_packet``
        method but can_handle provides a neat interface to ignore errors and
        see if the packet is good.

        :param data: bytearray to be verified
        :type data: bytearray

        :return: The formatted bytes as a readable hex string.
        :rtype: boolean
        """

        try:
            return self.validate_packet(data)
        except RFXComException:
            return False

    def validate_packet(self, data):
        """Validate a packet against this packet handler and determine if it
        meets the requirements. This is done by checking the following
        conditions are true.

        - The length of the packet is equal to the first byte.
        - The second byte is in the set of defined PACKET_TYPES for this class.
        - The third byte is in the set of this class defined PACKET_SUBTYPES.

        If one or more of these conditions isn't met then we have a packet that
        isn't valid or at least isn't understood by this handler.

        :param data: bytearray to be verified
        :type data: bytearray


        :raises: :py:class:`rfxcom.exceptions.InvalidPacketLength`: If the
            number of bytes in the packet doesn't match the expected length.

        :raises: :py:class:`rfxcom.exceptions.UnknownPacketType`: If the packet
            type is unknown to this packet handler

        :raises: :py:class:`rfxcom.exceptions.UnknownPacketSubtype`: If the
            packet sub type is unknown to this packet handler

        :return: true is returned if validation passes.
        :rtype: boolean

        """

        # Validate length.
        # The first byte in the packet should be equal to the number of
        # remaining bytes (i.e. length excluding the first byte).
        expected_length = data[0] + 1

        if len(data) != expected_length:
            raise InvalidPacketLength(
                "Expected packet length to be %s bytes but it was %s bytes"
                % (expected_length, len(data))
            )

        # Validate minimal length.
        # The packet contains at least the RFX header:
        #  packet_length (1 byte) + packet_type (1 byte)
        #  + packet_subtype (1 byte) + sequence_number (1 byte)
        if expected_length < 4:
            raise MalformedPacket(
                    "Expected packet length to be larger than 4 bytes but \
                    it was %s bytes"
                    % (len(data))
            )

        # Validate Packet Type.
        # This specifies the family of devices.
        # Check it is one of the supported packet types
        packet_type = data[1]

        if self.PACKET_TYPES and packet_type not in self.PACKET_TYPES:
            types = ",".join("0x{:02x}".format(pt) for pt in self.PACKET_TYPES)
            raise UnknownPacketType(
                "Expected packet type to be one of [%s] but recieved %s"
                % (types, packet_type)
            )

        # Validate Packet Subtype.
        # This specifies the sub-family of devices.
        # Check it is one of the supported packet subtypes for current type
        sub_type = data[2]

        if self.PACKET_SUBTYPES and sub_type not in self.PACKET_SUBTYPES:
            types = \
                ",".join("0x{:02x}".format(pt) for pt in self.PACKET_SUBTYPES)
            raise UnknownPacketSubtype(
                "Expected packet type to be one of [%s] but recieved %s"
                % (types, sub_type))

        return True

    def __str__(self):
        return "<{0} ID:{1}>".format(
            self.__class__.__name__, self.data.get('id'))


class Packet(BasePacket):
    """The Packet class is a base class that can be used for all data packets.
    It is a dumb class that accepts any data and doesn't validate it. However,
    it means that unrecognised packets can be handled in a similar way to those
    that are seen to be from a particular type of device.
    """

    def can_handle(self, data):
        return True

    def parse(self, data):

        packet_length = data[0]
        packet_type = data[1]
        sub_type = data[2]

        return {
            'packet_length': packet_length,
            'packet_type': packet_type,
            'packet_subtype': sub_type,
            'packet': data,
        }
