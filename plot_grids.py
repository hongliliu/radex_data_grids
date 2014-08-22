#!/Library/Frameworks/Python.framework/Versions/Current/bin/python
from pylab import *
from astropy.io import fits
from agpy import readcol#,asinh_norm
import matplotlib
from scipy import interpolate
import warnings
#import sys


"""
Two procedures:
    plot_radex is for contour plotting a subset of a radex cube
    gridcube is to turn a parameter cube into a .fits data cube

Dependencies: 
    agpy
    pyfits
    pylab
    matplotlib
"""

def plot_radex(filename,ngridpts=100,ncontours=50,plottype='ratio',
        transition="noname",thirdvarname="Temperature",
        cutnumber=None,cutvalue=10,vmin=None,vmax=None,logscale=False,
        save=True,**kwargs):
    """
    Create contour plots in density/column, density/temperature, or column/temperature
    filename - Name of the .dat file generated by radex_grid.py
    ngridpts - number of points in grid to interpolate onto
    ncontours - number of contours / colors
    plottype - can be 'ratio','tau1','tau2','tex1','tex2'
    transition - The name of the transition, e.g. "1-1_2-2".  Only used for saving
    thirdvarname - Third variable, i.e. the one that will be cut through.  If you want
        a density/column plot, choose temperature
    cutnumber - Cut on the cutnumber value of thirdvar.  e.g., if there are 5 temperatures 
        [10,20,30,40,50] and you set cutnumber=3, a temperature of 40K will be used
    cutvalue - Cut on this value; procedure will fail if there are no columns with this value
    vmin - Can force vmin/vmax in plotting procedures
    vmax - Can force vmin/vmax in plotting procedures
    logscale - takes log10 of plotted value before contouring 
    save - save the figure as a png?
    """

    names,props = readcol(filename,twod=False,names=True)
    temperature,density,column,tex1,tex2,tau1,tau2,tline1,tline2,flux1,flux2 = props
    #ratio = flux1 / flux2

    if thirdvarname == "Temperature":
      firstvar = density
      secondvar = column
      thirdvar = temperature
      if cutnumber is not None:
        cutvalue = unique(thirdvar)[int(cutnumber)]
      firstlabel = "log$(n_{H_2}) ($cm$^{-3})$"
      secondlabel = "log$(N_{H_2CO}) ($cm$^{-2})$"
      savetype = "DenCol_T=%iK" % cutvalue
      graphtitle = "T = %g K" % cutvalue
      firstvar = temperature
      secondvar = column
      thirdvar = density
      if cutnumber is not None:
        cutvalue = unique(thirdvar)[int(cutnumber)]
      firstlabel = "Temperature (K)"
      secondlabel = "log$(N_{H_2CO}) ($cm$^{-2})$"
      savetype = "TemCol_n=1e%gpercc" % cutvalue
      graphtitle = "n = %g cm$^{-3}$" % (10**cutvalue)
    elif thirdvarname == "Column":
      secondvar = density
      firstvar = temperature
      thirdvar = column
      if cutnumber is not None:
        cutvalue = unique(thirdvar)[int(cutnumber)]
      secondlabel = "log$(n_{H_2}) ($cm$^{-3})$"
      firstlabel = "Temperature (K)"
      savetype = "TemDen_N=1e%gpersc" % cutvalue
      graphtitle = "N = %g cm$^{-2}$" % (10**cutvalue)

    if plottype == 'ratio':
      cblabel = "$F_{1-1} / F_{2-2}$"
    elif plottype == 'tau1':
      cblabel = "$\\tau_{1-1}$"
    elif plottype == 'tau2':
      cblabel = "$\\tau_{2-2}$"
    elif plottype == 'tex1':
      cblabel = "$\\T_{ex}(1-1)$"
    elif plottype == 'tex2':
      cblabel = "$\\T_{ex}(2-2)$"

    varfilter = (thirdvar==cutvalue)
    if varfilter.sum() == 0:
      raise ValueError("Cut value %g does not match any of %s values" % (cutvalue, thirdvarname))

    nx = len(unique(firstvar))
    ny = len(unique(secondvar))
    if firstvar is temperature:
      firstarr = linspace((firstvar.min()),(firstvar.max()),nx)
    else:
      firstarr = linspace(firstvar.min(),firstvar.max(),nx)
    secondarr = linspace(secondvar.min(),secondvar.max(),ny)

    exec('plotdata = %s' % plottype)

    #plot_grid = griddata(firstvar[varfilter],secondvar[varfilter],plotdata[varfilter],firstarr,secondarr,interp='linear')
    plot_grid = interpolate.griddata(np.array([ firstvar[varfilter],
                                                secondvar[varfilter]
                                              ]).T,
                                     plotdata[varfilter],
                                     tuple(np.meshgrid(firstarr,secondarr)) )
    
    if vmax:
      plot_grid[plot_grid > vmax] = vmax
    if vmin:
      plot_grid[plot_grid > vmin] = vmin
    if logscale:
      plot_grid = log10(plot_grid)

    figure(1)
    clf()
    conlevs = logspace(-3,1,ncontours)
    contourf(firstarr,secondarr,plot_grid,conlevs,norm=matplotlib.colors.LogNorm())#,**kwargs) #,norm=asinh_norm.AsinhNorm(**kwargs),**kwargs)
    xlabel(firstlabel)
    ylabel(secondlabel)
    title(graphtitle)
    cb = colorbar()
    cb.set_label(cblabel)
    cb.set_ticks([1e-3,1e-2,1e-1,1,1e1])
    cb.set_ticklabels([1e-3,1e-2,1e-1,1,1e1])
    if save: savefig("%s_%s_%s.png" % (savetype,plottype,transition))

def gridcube(filename, outfilename, var1="density", var2="column",
             var3="temperature", var4=None, plotvar="tau1", zerobads=True,
             ratio_type='flux', round=2):
    """
    Reads in a radex_grid.py generated .dat file and turns it into a .fits data cube.
    filename - input .dat filename
    outfilename - output data cube name
    var1/var2/var3 - which variable will be used along the x/y/z axis?
    plotvar - which variable will be the value in the data cube?
    zerobads - set inf/nan values in plotvar to be zero
    """

    names,props = readcol(filename,twod=False,names=True)
    if round:
        for ii,name in enumerate(names):
            if name in ('Temperature','log10(dens)','log10(col)','opr'):
                props[ii] = np.round(props[ii],round)
    if var4 is None:
        temperature,density,column,tex1,tex2,tau1,tau2,tline1,tline2,flux1,flux2 = props
    else:
        temperature,density,column,opr,tex1,tex2,tau1,tau2,tline1,tline2,flux1,flux2 = props
        opr = np.floor(opr*100)/100.
    if ratio_type == 'flux':
        ratio = flux1 / flux2
    else:
        ratio = tau1 / tau2

    vardict = {
      "temperature":temperature,
      "density":density,
      "column":column,
      "tex1":tex1,
      "tex2":tex2,
      "tau1":tau1,
      "tau2":tau2,
      "tline1":tline1,
      "tline2":tline2,
      "flux1":flux1,
      "flux2":flux2,
      "ratio":ratio,
      }
    if var4 is not None:
        vardict['opr'] = opr

    nx = len(unique(vardict[var1]))
    ny = len(unique(vardict[var2]))
    nz = len(unique(vardict[var3]))
    if var4 is not None:
        nw = len(unique(vardict[var4]))

    xarr = (unique(vardict[var1])) #linspace(vardict[var1].min(),vardict[var1].max(),nx)
    yarr = (unique(vardict[var2])) #linspace(vardict[var2].min(),vardict[var2].max(),ny)
    zarr = (unique(vardict[var3])) #linspace(vardict[var2].min(),vardict[var2].max(),ny)
    if var4 is not None:
        warr = (unique(vardict[var4])) #linspace(vardict[var2].min(),vardict[var2].max(),ny)

    if var4 is None:
        newarr = zeros([nz,ny,nx])
    else:
        newarr = zeros([nw,nz,ny,nx])
    print "Cube shape will be ",newarr.shape

    if zerobads:
        pv = vardict[plotvar]
        pv[pv!=pv] = 0.0
        pv[isinf(pv)] = 0.0

    if var4 is None:
        for ival,val in enumerate(unique(vardict[var3])):
          varfilter = vardict[var3]==val
          #newarr[ival,:,:] = griddata((vardict[var1][varfilter]),(vardict[var2][varfilter]),vardict[plotvar][varfilter],xarr,yarr,interp='linear')
          newarr[ival,:,:] = interpolate.griddata(np.array([ vardict[var1][varfilter],vardict[var2][varfilter] ]).T,
                                                  vardict[plotvar][varfilter],
                                                  tuple(np.meshgrid(xarr,yarr)) )
    else:
        for ival4,val4 in enumerate(unique(vardict[var4])):
            for ival3,val3 in enumerate(unique(vardict[var3])):
              varfilter = (vardict[var3]==val3) * (vardict[var4]==val4)
              #newarr[ival4,ival3,:,:] = griddata((vardict[var1][varfilter]),(vardict[var2][varfilter]),vardict[plotvar][varfilter],xarr,yarr,interp='linear')
              if np.count_nonzero(varfilter) == 0:
                  warnings.warn("ERROR: There are no matches for {var3} == {val3} and {var4} == {val4}".format(val3=val3, val4=val4, var3=var3, var4=var4))
                  continue
              newarr[ival4,ival3,:,:] = interpolate.griddata(np.array([ vardict[var1][varfilter],vardict[var2][varfilter] ]).T,
                                                             vardict[plotvar][varfilter],
                                                             tuple(np.meshgrid(xarr,yarr)) )

    newfile = fits.PrimaryHDU(newarr)
    if var4 is not None:
        newfile.header.update('CRVAL4' ,  (min(warr)) )
        newfile.header.update('CRPIX4' ,  1 )
        newfile.header.update('CTYPE4' ,  'NLIN-OPR' )
        newfile.header.update('CDELT4' , (unique(warr)[1]) - (unique(warr)[0]) )
    newfile.header.update('BTYPE' ,  plotvar )
    newfile.header.update('CRVAL3' ,  (min(zarr)) )
    newfile.header.update('CRPIX3' ,  1 )
    if len(unique(zarr)) == 1:
        newfile.header.update('CTYPE3' ,  'ONE-TEMP' )
        newfile.header.update('CDELT3' , zarr[0])
    else:
        newfile.header.update('CTYPE3' ,  'LIN-TEMP' )
        newfile.header.update('CDELT3' , (unique(zarr)[1]) - (unique(zarr)[0]) )
    newfile.header.update('CRVAL1' ,  min(xarr) )
    newfile.header.update('CRPIX1' ,  1 )
    newfile.header.update('CD1_1' , xarr[1]-xarr[0] )
    newfile.header.update('CTYPE1' ,  'LOG-DENS' )
    newfile.header.update('CRVAL2' ,  min(yarr) )
    newfile.header.update('CRPIX2' ,  1 )
    newfile.header.update('CD2_2' , yarr[1]-yarr[0] )
    newfile.header.update('CTYPE2' ,  'LOG-COLU' )
    newfile.writeto(outfilename,clobber=True)


if __name__ == "__main__": 

    """
    You can call this code from the command line (though ideally in ipython):
      %run plot_grids.py filename (transition) (plottype) (cutnumber)
      ./plot_grids.py filename (transition) (plottype) (cutnumber)
    Command-line calls will plot cuts of temperature, density, and column.

    transition - name of transition (if not specified, defaults to the first 7
                 characters of the filename)
    plottype - Which value will be plotted?  defaults to "ratio", which is the 
               ratio of line-integrated flux
    cutnumber - which tem/den/col to use?

    Note that the plot labels default to H2CO labels; you'll have to hack the
    source code above in order to get the right transition labels to show up
    """
    import optparse

    parser=optparse.OptionParser()
    parser.add_option("--script",help="Grid all of the data into FITS cubes as a script?",action='store_true',default=False)
    parser.add_option("--transition",help="What transition (transition - The name of the transition, e.g. \"1-1_2-2\".  Only used for saving plots)",default=None)
    parser.add_option("--var4",help="Is the grid 4-dimensional (default is 3)? If yes, this should be a variable name.",default=None)
    parser.add_option("--plottype",help="If you're plotting, what do you want to plot?",default='ratio')
    parser.add_option("--cutnumber",help="Specifies a 'slice' location along the third dimension",default=0)
    parser.set_usage("%prog filename.dat [options]")
    parser.set_description(
    """
    Plotting & Gridding routine for RADEX data
    """)

    options,args = parser.parse_args()

    filename = args[0]

    if options.transition is not None:
        transition = options.transition
    else:
        transition = filename[:7]

    # allow %run to just run a script
    # Users, change this code to fit your needs!
    if options.script:
        prefix = filename.replace(".dat","")
        gridcube(prefix+'.dat',prefix+'_tau1.fits',plotvar='tau1',var4=options.var4)
        gridcube(prefix+'.dat',prefix+'_tau2.fits',plotvar='tau2',var4=options.var4)
        gridcube(prefix+'.dat',prefix+'_tex1.fits',plotvar='tex1',var4=options.var4)
        gridcube(prefix+'.dat',prefix+'_tex2.fits',plotvar='tex2',var4=options.var4)
        gridcube(prefix+'.dat',prefix+'_tline1.fits',plotvar='tline1',var4=options.var4)
        gridcube(prefix+'.dat',prefix+'_tline2.fits',plotvar='tline2',var4=options.var4)
        gridcube(prefix+'.dat',prefix+'_flux1.fits',plotvar='flux1',var4=options.var4)
        gridcube(prefix+'.dat',prefix+'_flux2.fits',plotvar='flux2',var4=options.var4)
        gridcube(prefix+'.dat',prefix+'_ratio.fits',plotvar='ratio',var4=options.var4)
      

    else:
        plot_radex(filename,transition=transition,plottype=options.plottype,cutnumber=int(options.cutnumber),thirdvarname="Temperature")
        plot_radex(filename,transition=transition,plottype=options.plottype,cutnumber=int(options.cutnumber),thirdvarname="Density")
        plot_radex(filename,transition=transition,plottype=options.plottype,cutnumber=int(options.cutnumber),thirdvarname="Column")

        show()
