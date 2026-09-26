"""Exercise signed pointers, song metadata and malformed blocks without music assets."""
import struct,unittest
from inspect_ay import inspect

def fixture():
    b=bytearray(104);b[:8]=b'ZXAYEMUL'
    def word(o,n):struct.pack_into('>H',b,o,n)
    def ptr(o,n):struct.pack_into('>h',b,o,n-o)
    b[20:24]=b'Test';b[24]=0;b[25:27]=b'X\0'
    ptr(12,20);ptr(14,25);ptr(18,32)
    ptr(32,20);ptr(34,40) # Song title deliberately uses a negative pointer.
    word(44,100);ptr(50,60);ptr(52,70)
    word(60,0xff00);word(62,0xc000);word(64,0xc003)
    word(70,0xc000);word(72,4);ptr(74,100);word(76,0)
    b[100:104]=b'\xc9\x00\x00\xc9';return b

class ParserTests(unittest.TestCase):
    def test_valid(self):
        r=inspect(fixture());self.assertEqual(r['title'],'Test');self.assertEqual(r['init'],0xc000)
        self.assertEqual(r['blocks'][0]['length'],4);self.assertEqual(r['length_ticks_50hz'],100)
    def test_bad_pointers_and_lengths(self):
        with self.assertRaises(ValueError):inspect(fixture(),1)
        with self.assertRaises(ValueError):inspect(fixture()[:-1])
        b=fixture();struct.pack_into('>h',b,18,-30)
        with self.assertRaises(ValueError):inspect(b)
        b=fixture();struct.pack_into('>H',b,70,65535)
        with self.assertRaises(ValueError):inspect(b)
if __name__=='__main__':unittest.main()
