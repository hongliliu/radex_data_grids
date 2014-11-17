"""
Create some simple grids for the 1mm para-H2CO lines

Used in the apex_h2co_mm project

"""
import pyradex
import pyradex.fjdu
import numpy as np
from astropy.utils.console import ProgressBar
from astropy.io import fits
from astropy import log
import warnings
# Make sure warnings are only shown once so the progressbar doesn't get flooded
warnings.filterwarnings('once')

ntemp,ndens,ncol = 50,20,20

temperatures = np.linspace(10,350,ntemp)
densities = np.linspace(2.5,7,ndens)
columns = np.linspace(11, 15.1, ncol)
abundance = 10**-8.5
abundance = 1.2e-9 # Johnston / Ao
opr = 0.01 # assume primarily para
opr = 3
fortho = opr/(1+opr)

import os
if not os.path.exists('ph2co-h2.dat'):
    import urllib
    urllib.urlretrieve('http://home.strw.leidenuniv.nl/~moldata/datafiles/ph2co-h2.dat')

def compute_grid(densities=densities, temperatures=temperatures,
                 columns=columns, fortho=fortho, deltav=5.0,
                 escapeProbGeom='lvg', Radex=pyradex.Radex,
                 run_kwargs={'reuse_last': True, 'reload_molfile': False}):

    # Initialize the RADEX fitter with some reasonable parameters
    R = Radex(species='ph2co-h2',
              column=1e14,
              temperature=50,
              escapeProbGeom=escapeProbGeom,
              collider_densities={'oH2':2e4*fortho,'pH2':2e4*(1-fortho)})

    R.run_radex()
    R.maxiter = 200

    # get the table so we can look at the frequency grid
    table = R.get_table()

    # Get warnings about temperature early
    R.temperature = temperatures.min()
    R.temperature = temperatures.max()

    # Target frequencies:
    #table[np.array([6,1,11])].pprint()

    key_303 = 2
    key_321 = 9
    key_322 = 12
    #key_303 = np.where((table['upperlevel'] == '3_0_3') &
    #                   (table['frequency'] > 218) &
    #                   (table['frequency'] < 220))[0]
    #key_321 = np.where((table['upperlevel'] == '3_2_1') &
    #                   (table['frequency'] > 218) &
    #                   (table['frequency'] < 220))[0]
    #key_322 = np.where((table['upperlevel'] == '3_2_2') &
    #                   (table['frequency'] > 218) &
    #                   (table['frequency'] < 220))[0]

    # used to assess where the grid failed
    bad_pars = []

    ndens = len(densities)
    ntemp = len(temperatures)
    ncols = len(columns)

    shape = [ntemp,ndens,ncols,]

    pars = dict(
        taugrid_303 = np.full(shape, np.nan),
        texgrid_303 = np.full(shape, np.nan),
        fluxgrid_303 = np.full(shape, np.nan),
        taugrid_321 = np.full(shape, np.nan),
        texgrid_321 = np.full(shape, np.nan),
        fluxgrid_321 = np.full(shape, np.nan),
        taugrid_322 = np.full(shape, np.nan),
        texgrid_322 = np.full(shape, np.nan),
        fluxgrid_322 = np.full(shape, np.nan),
    )

    for kk,tt in enumerate(ProgressBar(temperatures)):
        R.temperature = tt
        for jj,dd in enumerate(densities):
            R.density = {'oH2':10**dd*fortho,'pH2':10**dd*(1-fortho)}
            for ii,cc in enumerate(columns):
                #R.abundance = abundance # reset column to the appropriate value
                R.column_per_bin = 10**cc
                R.deltav = deltav
                #niter = R.run_radex(reuse_last=False, reload_molfile=True)
                niter = R.run_radex(**run_kwargs)

                if niter == R.maxiter:
                    bad_pars.append([tt,dd,cc])

                TI = R.source_line_surfbrightness
                pars['taugrid_303'][kk,jj,ii] = R.tau[key_303]
                pars['texgrid_303'][kk,jj,ii] = R.tex[key_303].value
                pars['fluxgrid_303'][kk,jj,ii] = TI[key_303].value
                pars['taugrid_321'][kk,jj,ii] = R.tau[key_321]
                pars['texgrid_321'][kk,jj,ii] = R.tex[key_321].value
                pars['fluxgrid_321'][kk,jj,ii] = TI[key_321].value
                pars['taugrid_322'][kk,jj,ii] = R.tau[key_322]
                pars['texgrid_322'][kk,jj,ii] = R.tex[key_322].value
                pars['fluxgrid_322'][kk,jj,ii] = TI[key_322].value

    return (TI, pars, bad_pars)

def makefits(data, btype, densities=densities, temperatures=temperatures,
             columns=columns, ):

    newfile = fits.PrimaryHDU(data=data)
    newfile.header.update('BTYPE' ,  btype )
    newfile.header.update('CRVAL3' ,  (min(temperatures)) )
    newfile.header.update('CRPIX3' ,  1 )
    if len(np.unique(temperatures)) == 1:
        newfile.header.update('CTYPE3' ,  'ONE-TEMP' )
        newfile.header.update('CDELT3' , temperatures[0])
    else:
        newfile.header.update('CTYPE3' ,  'LIN-TEMP' )
        newfile.header.update('CDELT3' , (np.unique(temperatures)[1]) - (np.unique(temperatures)[0]) )
    newfile.header.update('CRVAL1' ,  min(densities) )
    newfile.header.update('CRPIX1' ,  1 )
    newfile.header.update('CDELT1' , densities[1]-densities[0] )
    newfile.header.update('CTYPE1' ,  'LOG-DENS' )
    newfile.header.update('CRVAL2' ,  min(columns) )
    newfile.header.update('CRPIX2' ,  1 )
    newfile.header.update('CDELT2' , columns[1]-columns[0] )
    newfile.header.update('CTYPE2' ,  'LOG-COLU' )
    return newfile

if __name__ == "__main__":
    import re
    bt = re.compile("tex|tau|flux")

    (fTI, fpars, fbad_pars) = compute_grid(Radex=pyradex.fjdu.Fjdu,
                                           run_kwargs={})
    
    for pn in fpars:
        btype = bt.search(pn).group()
        ff = makefits(fpars[pn], btype, densities=densities,
                      temperatures=temperatures, columns=columns)
        outfile = 'fjdu_pH2CO_{line}_{type}_{dv}.fits'.format(line=pn[-3:],
                                                              type=btype,
                                                              dv='5kms')
        ff.writeto(outfile,
                   clobber=True)
        print outfile

    (TI, pars, bad_pars) = compute_grid()

    for pn in pars:
        btype = bt.search(pn).group()
        ff = makefits(pars[pn], btype, densities=densities,
                      temperatures=temperatures, columns=columns)
        outfile = 'pH2CO_{line}_{type}_{dv}.fits'.format(line=pn[-3:],
                                                          type=btype,
                                                          dv='5kms')
        ff.writeto(outfile,
                   clobber=True)
        print outfile

    log.info("FJDU had {0} bad pars".format(len(fbad_pars)))
    log.info("RADEX had {0} bad pars".format(len(bad_pars)))
    

    # look at differences
    for pn in pars:
        btype = bt.search(pn).group()
        outfile = 'pH2CO_{line}_{type}_{dv}.fits'.format(line=pn[-3:],
                                                          type=btype,
                                                          dv='5kms')
        header = fits.getheader(outfile)
        im1 = fits.getdata('fjdu_'+outfile)
        im2 = fits.getdata(outfile)
        hdu = fits.PrimaryHDU(data=im1-im2, header=header)
        hdu.writeto('diff_fjdu-radex_'+outfile, clobber=True)

