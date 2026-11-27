set -e
export PATH=/tmp/ep036tools/bin:$PATH
cd /tmp/ep036src/llama.cpp
cmake -S . -B build-native -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF
cmake --build build-native -j4 --target llama-bench llama-cli llama-simple llama-completion 2>&1 | tail -3 || cmake --build build-native -j4 --target llama-bench 2>&1 | tail -3
cmake -S . -B build-avx2 -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DGGML_AVX512=OFF -DGGML_AVX512_VNNI=OFF -DGGML_AVX_VNNI=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF
cmake --build build-avx2 -j4 --target llama-bench 2>&1 | tail -3
echo BUILD_DONE
