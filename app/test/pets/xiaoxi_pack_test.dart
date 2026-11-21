import 'dart:async';
import 'dart:ui' as ui;

import 'package:dsh_app/pets/pet_pack.dart';
import 'package:dsh_app/pets/pet_prefs.dart';
import 'package:dsh_app/pets/pet_state.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('小汐包覆盖现有状态、手势与图集边界', () async {
    expect(builtInPets, [defaultPetId]);
    final pack = await PetPack.load(defaultPetId);
    expect(pack.name, '小汐');
    for (final state in PetStateName.values) {
      final animation = pack.animFor(state);
      expect(animation.name, state.name);
      expect(animation.frames.length, greaterThan(1));
    }
    expect(pack.roam.name, 'roam');
    expect(pack.mirrorWalking(right: true), isTrue);
    for (final gesture in ['tapLeft', 'tapRight', 'tickle', 'drag']) {
      expect(pack.reaction(gesture), isNotNull);
    }
    final base = PetPack.folder(defaultPetId);
    for (final animation in pack.animations.values) {
      final bytes = await rootBundle.load('$base/${animation.sheet}');
      final codec = await ui.instantiateImageCodec(bytes.buffer.asUint8List());
      final image = (await codec.getNextFrame()).image;
      for (final frame in animation.frames) {
        final cell = animation.sourceRect(frame.i);
        expect(cell.right, lessThanOrEqualTo(image.width));
        expect(cell.bottom, lessThanOrEqualTo(image.height));
      }
      image.dispose();
      codec.dispose();
    }
  });

  test('旧上游桌宠目录不会随 Flutter 资源打包', () async {
    final manifest = await AssetManifest.loadFromAssetBundle(rootBundle);
    final sources = manifest.listAssets().where((path) => path.startsWith('assets/pets/'));
    expect(sources, isNotEmpty);
    expect(sources.every((path) => path.startsWith('assets/pets/xiaoxi/')), isTrue);
  });

  test('轻量模式下，显式选择的旧桌宠迁移为小汐', () async {
    SharedPreferences.setMockInitialValues({'performance.mode': 'light', 'pet.pack': 'whale-girl'});
    final container = ProviderContainer();
    addTearDown(container.dispose);
    final loaded = Completer<PetPrefs>();
    container.listen(petPrefsProvider, (_, next) {
      if (next.loaded && !loaded.isCompleted) loaded.complete(next);
    }, fireImmediately: true);
    final prefs = await loaded.future;
    expect(prefs.packId, defaultPetId);
    expect(prefs.packExplicit, isTrue);
  });
}
