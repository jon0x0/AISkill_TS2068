"""Synthetic invariants; no copyrighted sample artwork required."""
import unittest
from PIL import Image
from ecm_art import convert,offset,make_gradient,pack,decode

class ConversionTests(unittest.TestCase):
    def test_screen_addressing_and_decode(self):
        self.assertEqual(len({offset(y)+x for y in range(192) for x in range(32)}),6144)
        bits=[[int(x%3==0) for x in range(256)] for y in range(192)]
        attrs=[[7]*32 for y in range(192)];b,a=pack(bits,attrs);im=decode(b,a)
        self.assertEqual(len(b),6144);self.assertEqual(im.getpixel((0,191)),(205,205,205));self.assertEqual(im.getpixel((1,191)),(0,0,0))
    def test_rigid_phases_and_alpha(self):
        bg=Image.new('RGBA',(16,3),(200,30,100,255));im=Image.new('RGBA',(16,3),(0,255,0,0))
        im.putpixel((4,1),(240,240,240,255));composite,phases=convert(im,bg,phase_step=1)
        self.assertEqual(composite.getpixel((0,0)),bg.getpixel((0,0))[:3])
        row=lambda b,y:''.join(f'{x:08b}' for x in b[offset(y):offset(y)+2])
        for shift,b,a,m in phases:
            original=row(phases[0][1],1)
            self.assertEqual(row(b,1),original[shift:]+original[:shift])
            self.assertEqual(a,phases[0][2]);self.assertEqual(set(a[offset(1):offset(1)+2]),{a[offset(1)]})
            self.assertEqual(row(m,1).count('0'),1)
            self.assertEqual(m[offset(191)+31],255,'Outside source rectangle preserves background')
        with self.assertRaises(ValueError):convert(im,bg,mode='cell',phase_step=1)
    def test_gradient_and_dimensions(self):
        im=make_gradient(8,5,[(1,(10,20,30)),(3,(110,120,130))])
        self.assertEqual(im.getpixel((0,0)),(10,20,30,255));self.assertEqual(im.getpixel((0,2)),(60,70,80,255));self.assertEqual(im.getpixel((0,4)),(110,120,130,255))
        with self.assertRaises(ValueError):make_gradient(8,5,[(3,(0,0,0)),(1,(255,255,255))])
        with self.assertRaises(ValueError):convert(Image.new('RGBA',(9,2)),Image.new('RGBA',(9,2)))
if __name__=='__main__':unittest.main()
