// Own validation code: CC0. Profiles apply only after an exact GLB SHA256 match.
const finiteArray = values => Array.isArray(values) && values.every(Number.isFinite);
const closeVector = (actual, expected, tolerance) => finiteArray(actual) && actual.length === expected.length && actual.every((value, i) => Math.abs(value - expected[i]) <= tolerance);

export function checksForProfile(profile, data) {
  const {samples, textures, vertexColors, jointDeltas, worldMotion, presentBones, skeletonJointCounts, nodeNames} = data;
  const common = {
    loaded: true,
    expectedClipPresent: data.clipName === profile.clip,
    skinnedMeshesPresent: data.skinnedMeshCount > 0,
    finiteDeformedVertices: samples.length === profile.sampleSpecs.length && samples.every(sample => sample.nonFiniteVertices === 0),
    allReferencedTextureImagesReady: textures.every(texture => texture.ready),
    loaderReportedNoMissingResources: data.loaderErrors.length === 0,
    expectedVertexPaintAndMaterialCount: Number.isInteger(profile.expectedMeshCount) && vertexColors.length === profile.expectedMeshCount,
    bakedVertexColorsPresentFiniteAndUsed: vertexColors.length > 0 && vertexColors.every(row => row.colorAttributePresent && row.finite && row.colorVertices === row.positionVertices && row.allMaterialsUseVertexColors),
    noRasterMapsExpectedOrMissing: textures.length === 0 && data.loaderErrors.length === 0
  };
  if (profile.motionMode === 'limbs_fk') {
    // Keep the original sixteen six-bone checks, including each limb's vertices.
    return {
      loaded: common.loaded,
      expectedClipPresent: common.expectedClipPresent,
      skinnedMeshesPresent: common.skinnedMeshesPresent,
      expectedSixBonesPresent: profile.expectedBones.every(bone => presentBones.includes(bone)),
      finiteDeformedVertices: common.finiteDeformedVertices,
      armsPoseChangesVertices: samples[1]?.maximumVertexDeltaFromRest > 1e-5,
      legsPoseChangesVertices: samples[2]?.maximumVertexDeltaFromRest > 1e-5,
      bothArmJointRotationsChange: ['arm.L','arm.R'].every(name => jointDeltas[1]?.[name] > 1e-5),
      bothLegJointRotationsChange: ['leg.L','leg.R'].every(name => jointDeltas[2]?.[name] > 1e-5),
      allReferencedTextureImagesReady: common.allReferencedTextureImagesReady,
      loaderReportedNoMissingResources: common.loaderReportedNoMissingResources,
      expectedVertexPaintAndMaterialCount: common.expectedVertexPaintAndMaterialCount,
      bakedVertexColorsPresentFiniteAndUsed: common.bakedVertexColorsPresentFiniteAndUsed,
      noRasterMapsExpectedOrMissing: common.noRasterMapsExpectedOrMissing,
      independentlyWeightedLeftAndRightArmsDeform: ['arm.L','arm.R'].every(name => {
        const limb = samples[1]?.limbDeformation?.[name];
        return !!limb && limb.dominantWeightedVertices > 0 && limb.movedVertices > 0 && limb.maximumVertexDeltaFromRest > 1e-5;
      }),
      independentlyWeightedLeftAndRightLegsDeform: ['leg.L','leg.R'].every(name => {
        const limb = samples[2]?.limbDeformation?.[name];
        return !!limb && limb.dominantWeightedVertices > 0 && limb.movedVertices > 0 && limb.maximumVertexDeltaFromRest > 1e-5;
      })
    };
  }
  if (profile.motionMode !== 'hop_tilt') throw new Error('未対応のmotionModeです');
  const expectation = profile.motionExpectations;
  const hopRoot = worldMotion[1]?.root;
  const tiltRoot = worldMotion[2]?.root;
  const hopBody = worldMotion[1]?.body;
  const tiltBody = worldMotion[2]?.body;
  const axis = ['x','y','z'].indexOf(expectation.tiltBodyWorldAxis);
  const rotation = tiltBody?.rotationDeltaQuaternionWorld;
  const axisCorrect = axis >= 0 && finiteArray(rotation) && rotation.length === 4 && rotation.slice(0,3).every((value, index) => index === axis || Math.abs(value) <= expectation.rotationTolerance);
  return {
    loaded: common.loaded,
    expectedClipPresent: common.expectedClipPresent,
    skinnedMeshesPresent: common.skinnedMeshesPresent,
    expectedTwoBonesPresent: presentBones.length === 2 && profile.expectedBones.every(bone => presentBones.includes(bone)) && skeletonJointCounts.length > 0 && skeletonJointCounts.every(row => row.joints === 2),
    finiteDeformedVertices: common.finiteDeformedVertices,
    hopPoseChangesVertices: samples[1]?.maximumVertexDeltaFromRest > 1e-5,
    tiltPoseChangesVertices: samples[2]?.maximumVertexDeltaFromRest > 1e-5,
    rootTranslationMatchesHop: closeVector(hopRoot?.translationDeltaWorld, expectation.hopRootTranslation, expectation.translationTolerance) && closeVector(tiltRoot?.translationDeltaWorld, [0,0,0], expectation.translationTolerance) && Number.isFinite(hopRoot?.rotationAngleRadians) && hopRoot.rotationAngleRadians <= expectation.rotationTolerance && Number.isFinite(tiltRoot?.rotationAngleRadians) && tiltRoot.rotationAngleRadians <= expectation.rotationTolerance,
    bodyRotationMatchesTilt: !!tiltBody && Number.isFinite(tiltBody.rotationAngleRadians) && Math.abs(tiltBody.rotationAngleRadians - expectation.tiltBodyAngleRadians) <= expectation.rotationTolerance && axisCorrect && Number.isFinite(jointDeltas[2]?.body) && Math.abs(jointDeltas[2].body-expectation.tiltBodyAngleRadians) <= expectation.rotationTolerance && Number.isFinite(hopBody?.rotationAngleRadians) && hopBody.rotationAngleRadians <= expectation.rotationTolerance && Number.isFinite(jointDeltas[1]?.body) && jointDeltas[1].body <= expectation.rotationTolerance && closeVector(hopBody?.translationDeltaLocal,[0,0,0],expectation.translationTolerance) && closeVector(tiltBody?.translationDeltaLocal,[0,0,0],expectation.translationTolerance),
    allReferencedTextureImagesReady: common.allReferencedTextureImagesReady,
    loaderReportedNoMissingResources: common.loaderReportedNoMissingResources,
    expectedVertexPaintAndMaterialCount: common.expectedVertexPaintAndMaterialCount,
    bakedVertexColorsPresentFiniteAndUsed: common.bakedVertexColorsPresentFiniteAndUsed,
    noRasterMapsExpectedOrMissing: common.noRasterMapsExpectedOrMissing,
    limbNodesAbsent: Array.isArray(profile.forbiddenNodePatterns) && profile.forbiddenNodePatterns.length > 0 && nodeNames.every(name => profile.forbiddenNodePatterns.every(pattern => !new RegExp(pattern,'i').test(name))),
    expectedMotionClipDuration: Number.isFinite(data.clipDurationSeconds) && Math.abs(data.clipDurationSeconds - profile.expectedClipDurationSeconds) <= 1e-5
  };
}
