import maya.cmds as cmds
import maya.OpenMayaUI as omui


from PySide2 import QtWidgets
from PySide2 import QtGui, QtCore
from shiboken2 import wrapInstance

from OpenEXR import OpenEXR as ox
from PIL import Image
import Imath
import math

import maya.OpenMaya as om

import dwUi
reload (dwUi)



def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_window_ptr), QtWidgets.QWidget)



class ControlMainWindow(QtWidgets.QWidget):
 
    def __init__(self, parent=None):

        super(ControlMainWindow, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.Tool)
        self.ui = dwUi.Ui_dwUI()
        self.ui.setupUi(self)
        self.displacementPath = ["none"]
        self.mesh = ["none"]
        self.shape = ["none"]
        self.MinLuma = ["none"]
        self.MaxLuma = ["none"]
        self.ui.pickMesh.clicked.connect(self.pickMesh)
        self.ui.pickMap.clicked.connect(self.pickMap)
        self.ui.setup.clicked.connect(self.displacementSetup)

#---------------------------------------------

    def pickMap(self):
        
        Filters = "Float Displacement texture files (*.exr *.tif .*tiff .*tex)"
        displacementFile = cmds.fileDialog2(dialogStyle=2, fileMode=1, fileFilter= Filters, cap ="Select the image file to load as displacement map",okc ="Pick")
        if displacementFile == None :
            return

        self.ui.pickMap.setText(displacementFile[0])
        self.displacementPath = displacementFile

#---------------------------------------------

    def pickMesh(self):
        
        selection = cmds.ls (selection=True)
        mesh = cmds.filterExpand(selection, sm=12)

        if  mesh == None:
            om.MGlobal.displayError("your selection is not a polygon mesh") 
            return 

        self.mesh = mesh
        self.ui.pickMesh.setText(mesh[0])
        self.shape = cmds.listRelatives(mesh, shapes=True)

        for node in mesh:
	        history = cmds.listHistory(node) or []
	        deformHistory = cmds.ls(history, type="geometryFilter", long=True)    
        
        if not deformHistory == []:
            om.MGlobal.displayWarning("mesh has deformer in history that might affect the displacement, don't forget to check them if the displacement isn't working as expected")

#---------------------------------------------

    def displacementSetup(self):
       
        storedSelection = cmds.ls(sl=True,long=True) or []
        DisplacementFile = self.displacementPath[0]
        mesh = self.mesh[0]
        RenderEngineValue = str(self.ui.RenderEngine.currentIndex())
        udimValue = str(self.ui.udim.isChecked())
        keepShaderValue = str(self.ui.keepShader.isChecked())
        currentEngine = cmds.getAttr("defaultRenderGlobals.currentRenderer")


        if DisplacementFile == "none" or mesh == "none":
            om.MGlobal.displayError("Please select a Map and a Polygon Mesh")
            return

        if RenderEngineValue == "0" and currentEngine =="arnold" :
            self.getLuma(DisplacementFile)
            self.arnoldMeshSetup(mesh)
            self.arnoldShaderSetup(mesh,keepShaderValue,udimValue,DisplacementFile)
            cmds.select(storedSelection)
            om.MGlobal.displayInfo("done")
            
            

        elif RenderEngineValue == "1" and currentEngine =="renderManRIS":
            currentEngine = "renderMan"
            self.renderManMeshSetup(mesh)
            self.rendermanShaderSetup(mesh,keepShaderValue,udimValue,DisplacementFile)
            cmds.select(storedSelection)
            om.MGlobal.displayInfo("done")
            


        elif RenderEngineValue == "2" and currentEngine =="vray":
            self.getLuma(DisplacementFile)
            self.vrayMeshSetup(mesh)
            self.vrayShaderSetup(mesh,keepShaderValue,udimValue,DisplacementFile)
            cmds.select(storedSelection)
            om.MGlobal.displayInfo("done")

        else:
            if RenderEngineValue == "0":
                RenderEngineValue = "arnold"
            elif RenderEngineValue == "1":
                RenderEngineValue = "renderMan"
            elif RenderEngineValue == "2":
                RenderEngineValue = "Vray"
            if currentEngine =="renderManRIS":
                currentEngine = "RenderMan"  
            om.MGlobal.displayError(" the current engine is "+ currentEngine +" not "+RenderEngineValue) 

#---------------------------------------------

    def getLuma(self,DisplacementFile):
        
        

        if str(DisplacementFile).endswith('.tif'):
            grayscale = Image.open(DisplacementFile)
            MinLuma, MaxLuma = grayscale.getextrema()
            
        
        elif str(DisplacementFile).endswith('.exr'):
            file = ox.InputFile(DisplacementFile)
            pt = Imath.PixelType(Imath.PixelType.FLOAT)
            dwin = file.header()['dataWindow']
            size = (dwin.max.x - dwin.min.x + 1, dwin.max.y - dwin.min.y + 1)

            rgbf = [Image.frombytes("F", size, file.channel(c, pt)) for c in "R"]

            extrema = [im.getextrema() for im in rgbf]
            MinLuma = min([lo for (lo,hi) in extrema])
            MaxLuma = max([hi for (lo,hi) in extrema])
            

        print '// max luma value is '+ str(MaxLuma)
        print '// max luma value is '+ str(MinLuma)        

        self.MinLuma = math.floor(MinLuma * 10000000.0) / 10000000.0
        self.MaxLuma = math.ceil(MaxLuma * 10000000.0) / 10000000.0

#---------------------------------------------

    def arnoldMeshSetup(self,mesh):
        shape = cmds.listRelatives(mesh, shapes=True)

        for shapes in shape:
            cmds.setAttr(shapes+".aiSubdivType" ,1)
            cmds.setAttr(shapes+".aiSubdivIterations" ,5)
            cmds.setAttr(shapes+".aiSubdivUvSmoothing" ,2)
            cmds.setAttr(shapes+".aiDispPadding" ,1)

#---------------------------------------------

    def renderManMeshSetup(self,mesh):

        shape = cmds.listRelatives(mesh, shapes=True)

        for shapes in shape:
            cmds.rman("addAttr",shapes,"rman__torattr___subdivScheme")
            cmds.rman("addAttr",shapes,"rman__torattr___subdivFacevaryingInterp")
            cmds.setAttr(shapes+'.rman__torattr___subdivFacevaryingInterp', 3)

#---------------------------------------------

    def vrayMeshSetup(self,mesh):

        shape = cmds.listRelatives(mesh, shapes=True) 

        for shapes in shape:
            cmds.vray("addAttributesFromGroup", shapes, "vray_subdivision", 1)
            cmds.vray("addAttributesFromGroup", shapes, "vray_subquality", 1)
            cmds.vray("addAttributesFromGroup", shapes, "vray_displacement", 1)
            cmds.setAttr(shapes+".vraySubdivEnable" ,1)
            cmds.setAttr(shapes+".vraySubdivUVs" ,0)
            cmds.setAttr(shapes+".vrayEdgeLength" ,4)
            cmds.setAttr(shapes+".vrayDisplacementType" ,1)
            cmds.setAttr(shapes+".vrayDisplacementKeepContinuity" ,1)
            cmds.setAttr(shapes+".vray2dDisplacementFilterTexture" ,0)
            cmds.setAttr(shapes+".vrayDisplacementUseBounds" ,1)

#---------------------------------------------

    def arnoldShaderSetup(self, mesh, keepShaderValue, udimValue,DisplacementFile):


        MaxBound = max([self.MinLuma, self.MaxLuma], key=abs) 

        if keepShaderValue == "False":
            shader = cmds.shadingNode("aiStandard", name = mesh + "_aiStandard", asShader=True)
            shading_group= cmds.sets(name = mesh + "SG", renderable=True,noSurfaceShader=True,empty=True)
            cmds.connectAttr('%s.outColor' %shader ,'%s.surfaceShader' %shading_group)

        else:
            shape = cmds.listRelatives(mesh, shapes=True)
            shading_group = cmds.listConnections(shape,type='shadingEngine')
                

        displacement_shader = cmds.shadingNode("displacementShader",name = mesh + "_displacementShader", asShader=True)
        file_node = cmds.shadingNode("file",name = mesh +"_displacement_File" , asTexture=True, isColorManaged = True)
        uv = cmds.shadingNode("place2dTexture", asUtility=True)

        cmds.setAttr(file_node+".filterType" ,0)
        cmds.setAttr(file_node+".fileTextureName" ,DisplacementFile, type = "string")
        cmds.setAttr(file_node+".colorSpace", "Raw", type="string")
        cmds.setAttr(mesh+".aiDispPadding" , MaxBound)


        if udimValue == "True":
            cmds.setAttr(file_node+".uvTilingMode", 3)
            cmds.setAttr(file_node+".uvTileProxyQuality", 4)

        if keepShaderValue == "False":
            cmds.connectAttr('%s.displacement' %displacement_shader ,'%s.displacementShader' %shading_group, force=True)
        else:
            cmds.connectAttr('%s.displacement' %displacement_shader ,'%s.displacementShader' %str(shading_group[0]), force=True)

        cmds.defaultNavigation(connectToExisting=True, source=uv , destination=file_node)

        cmds.connectAttr('%s.outColorR' %file_node, '%s.displacement' %displacement_shader)
        cmds.select(cmds.listRelatives(mesh, shapes=True))

        if keepShaderValue == "False":
            cmds.hyperShade(assign=shading_group)

#---------------------------------------------

    def rendermanShaderSetup(self, mesh, keepShaderValue, udimValue,DisplacementFile):

        if keepShaderValue == "False":
            shader = cmds.shadingNode("PxrSurface", name = mesh +"_PxrSurface", asShader=True)        
            shading_group= cmds.sets(name = mesh + "SG", renderable=True,noSurfaceShader=True,empty=True)
            cmds.connectAttr('%s.outColor' %shader ,'%s.surfaceShader' %shading_group)

        else:
            shape = cmds.listRelatives(mesh, shapes=True)
            shading_group = cmds.listConnections(shape,type='shadingEngine')
                

        displacement_shader = cmds.shadingNode("PxrDisplace",name = mesh + "_PxrDisplace", asShader=True)
        displacement_transform = cmds.shadingNode("PxrDispTransform",name = mesh + "_PxrDispTransform", asUtility=True)
        file_node = cmds.shadingNode("PxrTexture",name = mesh +"_Displacement_PxrTexture" , asTexture=True,)
        uv = cmds.shadingNode("place2dTexture", asUtility=True)

        cmds.setAttr(file_node+".filter" , 0)
        cmds.setAttr(displacement_transform+".dispType", 1)
        cmds.setAttr(displacement_transform+".dispHeight", 1.2)
        cmds.setAttr(displacement_transform+".dispDepth", 1.2)


        if udimValue == "True":

            udimcoords = range(1001,1999)

            for coords in udimcoords:
               DisplacementFile = DisplacementFile.replace(str(coords), '_MAPID_')
            cmds.setAttr(file_node+".filename" ,DisplacementFile, type = "string")
            cmds.setAttr(file_node+".atlasStyle", 1)

        cmds.setAttr(file_node+".filename" ,DisplacementFile, type = "string")

        if keepShaderValue == "False":
            cmds.connectAttr('%s.outColor' %displacement_shader ,'%s.displacementShader' %shading_group, force=True)
        else:
            cmds.connectAttr('%s.outColor' %displacement_shader ,'%s.displacementShader' %str(shading_group[0]), force=True)


        cmds.connectAttr('%s.resultR' %file_node, '%s.dispScalar' %displacement_transform)
        cmds.connectAttr('%s.resultF' %displacement_transform, '%s.dispScalar' %displacement_shader)
        cmds.select(cmds.listRelatives(mesh, shapes=True))

        if keepShaderValue == "False":
            cmds.hyperShade(assign=shading_group)

#---------------------------------------------

    def vrayShaderSetup(self, mesh, keepShaderValue, udimValue,DisplacementFile):


        if keepShaderValue == "False":
            shader = cmds.shadingNode("VRayMtl", name = mesh +"_VRayMtl", asShader=True)        
            shading_group= cmds.sets(name = mesh + "SG", renderable=True,noSurfaceShader=True,empty=True)
            cmds.connectAttr('%s.outColor' %shader ,'%s.surfaceShader' %shading_group)
        else:
            shape = cmds.listRelatives(mesh, shapes=True)
            shading_group = cmds.listConnections(shape,type='shadingEngine')
  
        displacement_shader = cmds.shadingNode("displacementShader",name = mesh + "_displacementShader", asShader=True)
        file_node = cmds.shadingNode("file",name = mesh +"_displacement_File" , asTexture=True, isColorManaged = True)
        uv = cmds.shadingNode("place2dTexture", asUtility=True)

        cmds.setAttr(file_node+".filterType" ,0)
        cmds.setAttr(file_node+".fileTextureName" ,DisplacementFile, type = "string")
        cmds.setAttr(file_node+".colorSpace", "Raw", type="string")


        if udimValue == "True":
            cmds.setAttr(file_node+".uvTilingMode", 3)
            cmds.setAttr(file_node+".uvTileProxyQuality", 4)
        else:
            cmds.addAttr(file_node, longName='MaxLumaValue', attributeType='double')
            cmds.addAttr(file_node, longName='MinLumaValue', attributeType='double')
            cmds.setAttr(file_node+".MaxLumaValue", self.MaxLuma)
            cmds.setAttr(file_node+".MinLumaValue", self.MinLuma)
            cmds.connectAttr('%s.MaxLumaValue' %file_node ,'%s.vrayDisplacementMaxValueR' %mesh, force=True)
            cmds.connectAttr('%s.MaxLumaValue' %file_node ,'%s.vrayDisplacementMaxValueG' %mesh, force=True)
            cmds.connectAttr('%s.MaxLumaValue' %file_node ,'%s.vrayDisplacementMaxValueB' %mesh, force=True)
            cmds.connectAttr('%s.MinLumaValue' %file_node ,'%s.vrayDisplacementMinValueR' %mesh, force=True)
            cmds.connectAttr('%s.MinLumaValue' %file_node ,'%s.vrayDisplacementMinValueG' %mesh, force=True)
            cmds.connectAttr('%s.MinLumaValue' %file_node ,'%s.vrayDisplacementMinValueB' %mesh, force=True);    

        if keepShaderValue == "False":
            cmds.connectAttr('%s.displacement' %displacement_shader ,'%s.displacementShader' %shading_group, force=True)
        else:
            cmds.connectAttr('%s.displacement' %displacement_shader ,'%s.displacementShader' %str(shading_group[0]), force=True)

        cmds.defaultNavigation(connectToExisting=True, source=uv , destination=file_node , quiet=True)
        
        cmds.connectAttr('%s.outColorR' %file_node, '%s.displacement' %displacement_shader)
        cmds.select(cmds.listRelatives(mesh, shapes=True))

        if keepShaderValue == "False":
            cmds.hyperShade(assign=shading_group)

#---------------------------------------------

def run():

    global win
    try:
        win.close()
        win.deleteLater()

    except: 
        pass

    win = ControlMainWindow(parent=maya_main_window())
    win.show()