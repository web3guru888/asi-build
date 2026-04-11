#!/usr/bin/env python3
"""
Demonstrate fully homomorphic encryption (FHE):
- Generate encryption keys (BGV scheme)
- Encrypt two integers
- Perform addition and multiplication on ciphertexts
- Decrypt and verify results

Requires: numpy
Note: This is a *pedagogical* FHE implementation. For production use,
      use a library like Microsoft SEAL, OpenFHE, or TenSEAL.
"""

from asi_build.homomorphic.core.base import FHEConfiguration, SchemeType, SecurityLevel
from asi_build.homomorphic.schemes.bgv import BGVScheme

print("=" * 60)
print("Fully Homomorphic Encryption — BGV Scheme Demo")
print("=" * 60)

# --- Step 1: Configure the BGV scheme ---
# BGV (Brakerski–Gentry–Vaikuntanathan) supports exact integer arithmetic.
config = FHEConfiguration(
    scheme_type=SchemeType.BGV,
    security_level=SecurityLevel.LOW,       # 128-bit (fine for demo)
    polynomial_modulus_degree=4096,          # power of 2
    coefficient_modulus=[1 << 40, 1 << 30, 1 << 30],  # modulus chain
    plaintext_modulus=257,                   # prime, operations mod 257
)

bgv = BGVScheme(config)
info = bgv.get_scheme_info()
print(f"\nScheme         : {info.get('scheme_type', 'BGV')}")
print(f"Security       : {config.security_level.value}")
print(f"Poly degree    : {config.polynomial_modulus_degree}")
print(f"Plaintext mod  : {config.plaintext_modulus}")
print(f"Batch slots    : {info.get('batch_slots', 'N/A')}")

# --- Step 2: Generate keys ---
print("\nGenerating keys (public, secret, relinearization, Galois)...")
keys = bgv.generate_keys()
print(f"  Public key        : {'✅' if keys['public_key'] else '❌'}")
print(f"  Secret key        : {'✅' if keys['secret_key'] else '❌'}")
print(f"  Relin keys        : {'✅' if keys['relinearization_keys'] else '❌'}")
print(f"  Galois keys       : {'✅' if keys['galois_keys'] else '—'}")

# --- Step 3: Encrypt two integers ---
a, b = 42, 17
print(f"\nPlaintext values: a = {a}, b = {b}")

ct_a = bgv.encrypt(a)
ct_b = bgv.encrypt(b)
print(f"  Encrypted a → {ct_a}")
print(f"  Encrypted b → {ct_b}")

# --- Step 4: Homomorphic addition (a + b) ---
ct_sum = bgv.add(ct_a, ct_b)
pt_sum = bgv.decrypt(ct_sum)
result_sum = pt_sum.integer_values[0] if pt_sum.integer_values else "?"
print(f"\nHomomorphic addition:")
print(f"  decrypt(enc(a) + enc(b)) = {result_sum}")
print(f"  Expected                 = {(a + b) % config.plaintext_modulus}")

# --- Step 5: Homomorphic multiplication (a × b) ---
ct_prod = bgv.multiply(ct_a, ct_b)
pt_prod = bgv.decrypt(ct_prod)
result_prod = pt_prod.integer_values[0] if pt_prod.integer_values else "?"
print(f"\nHomomorphic multiplication:")
print(f"  decrypt(enc(a) × enc(b)) = {result_prod}")
print(f"  Expected                 = {(a * b) % config.plaintext_modulus}")

# --- Step 6: Add a plaintext to a ciphertext ---
c = 10
ct_add_plain = bgv.add_plain(ct_a, c)
pt_add_plain = bgv.decrypt(ct_add_plain)
result_add_plain = pt_add_plain.integer_values[0] if pt_add_plain.integer_values else "?"
print(f"\nCiphertext + plaintext:")
print(f"  decrypt(enc(a) + {c}) = {result_add_plain}")
print(f"  Expected              = {(a + c) % config.plaintext_modulus}")

# --- Note about noise budget ---
print(f"\n💡 Note: Each homomorphic operation adds noise to the ciphertext.")
print(f"   After enough operations the result becomes unrecoverable.")
print(f"   BGV uses modulus switching to manage noise between operations.")

print("\n✅ Homomorphic encryption demo complete.")
